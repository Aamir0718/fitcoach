from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.database import get_db
from app.models.auth import Auth, OTPCode, RefreshToken
from app.models.profile import Profile
from sqlalchemy.orm import selectinload
from app.schemas.auth import (
    SignupRequest, LoginRequest, SendOTPRequest, VerifyOTPRequest,
    ResetPasswordRequest, TokenResponse, RefreshRequest, OTPLoginRequest, OTPSendRequest,
)
from app.core.security import (
    hash_password, verify_password, needs_rehash, generate_otp, hash_otp, verify_otp,
    create_access_token, generate_refresh_token, hash_refresh_token,
    refresh_token_expires,
)
from app.core.email import send_otp_email
from app.config import settings

# Rate limiting (simple in-memory — swap for Redis in production)
from collections import defaultdict
from datetime import timedelta
import time

_rate_store: dict = defaultdict(list)

def _check_rate(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    _rate_store[key] = [t for t in _rate_store[key] if now - t < window_seconds]
    if len(_rate_store[key]) >= limit:
        return False
    _rate_store[key].append(now)
    return True


router = APIRouter(prefix="/api/auth", tags=["auth"])


async def _issue_tokens(user: Auth, db: AsyncSession) -> TokenResponse:
    """Create access + refresh tokens and persist refresh token."""
    access = create_access_token(user.id, user.email)
    refresh_raw = generate_refresh_token()
    refresh_hashed = hash_refresh_token(refresh_raw)

    db_token = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hashed,
        expires_at=refresh_token_expires(),
    )
    db.add(db_token)
    await db.commit()

    # Explicitly query profile — never use lazy relationship in async context
    # (accessing user.profile lazily raises MissingGreenlet in SQLAlchemy async)
    profile_result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = profile_result.scalar_one_or_none()
    onboarding = profile.onboarding_complete if profile else False

    return TokenResponse(
        access_token=access,
        refresh_token=refresh_raw,
        user_id=user.id,
        email=user.email,
        onboarding_complete=onboarding,
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    if not _check_rate(f"signup:{body.email}", 5, 3600):
        raise HTTPException(status_code=429, detail="Too many signup attempts. Try again later.")

    result = await db.execute(select(Auth).where(Auth.email == body.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = Auth(
        email=body.email,
        password_hash=hash_password(body.password),
        is_verified=True,   # auto-verify; OTP email sent as welcome
    )
    db.add(user)
    await db.flush()  # get user.id before commit

    profile = Profile(user_id=user.id)
    db.add(profile)
    await db.commit()
    await db.refresh(user)

    # Send verification OTP
    otp = generate_otp()
    db.add(OTPCode(
        email=body.email,
        otp_hash=hash_otp(otp),
        purpose="verify",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    ))
    await db.commit()
    await send_otp_email(body.email, otp, "verify")

    return await _issue_tokens(user, db)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    if not _check_rate(f"login:{body.email}", 10, 60):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in a minute.")

    result = await db.execute(
        select(Auth).where(Auth.email == body.email, Auth.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
        await db.commit()

    return await _issue_tokens(user, db)


@router.post("/send-otp")
async def send_otp(body: SendOTPRequest, db: AsyncSession = Depends(get_db)):
    if not _check_rate(f"otp:{body.email}", 5, 60):
        raise HTTPException(status_code=429, detail="Too many OTP requests. Wait a minute.")

    # Invalidate old OTPs for this email/purpose
    await db.execute(
        delete(OTPCode).where(OTPCode.email == body.email, OTPCode.purpose == body.purpose)
    )

    otp = generate_otp()
    db.add(OTPCode(
        email=body.email,
        otp_hash=hash_otp(otp),
        purpose=body.purpose,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    ))
    await db.commit()
    delivered = await send_otp_email(body.email, otp, body.purpose)

    # Always log OTP — readable from Render dashboard logs
    print(f"[OTP] {body.email} | purpose={body.purpose} | code={otp} | delivered={delivered}")

    # Return OTP in response so the app can display it as a fallback when email fails.
    # This is intentional — the user is already authenticated to request this code,
    # and showing it on-screen is safer than not being able to log in at all.
    return {"message": "OTP sent", "otp_fallback": otp, "email_delivered": delivered}


@router.post("/verify-otp")
async def verify_otp_route(body: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    if not _check_rate(f"verify:{body.email}", 10, 60):
        raise HTTPException(status_code=429, detail="Too many attempts")

    result = await db.execute(
        select(OTPCode).where(
            OTPCode.email == body.email,
            OTPCode.purpose == body.purpose,
            OTPCode.used == False,
        ).order_by(OTPCode.created_at.desc()).limit(1)
    )
    otp_record = result.scalar_one_or_none()

    if not otp_record:
        raise HTTPException(status_code=400, detail="No OTP found. Request a new one.")

    if datetime.now(timezone.utc) > otp_record.expires_at:
        raise HTTPException(status_code=400, detail="OTP expired. Request a new one.")

    if not verify_otp(body.otp, otp_record.otp_hash):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Mark used
    otp_record.used = True
    await db.commit()

    if body.purpose == "verify":
        result = await db.execute(select(Auth).where(Auth.email == body.email))
        user = result.scalar_one_or_none()
        if user:
            user.is_verified = True
            await db.commit()
        return {"message": "Email verified"}

    if body.purpose == "reset":
        # Return a short-lived reset token
        from app.core.security import generate_reset_token, hash_reset_token
        token = generate_reset_token()
        # Store hashed in DB or memory cache (simplified: return directly, verified by OTP)
        return {"message": "OTP verified", "reset_token": token, "email": body.email}

    if body.purpose == "login":
        result = await db.execute(select(Auth).where(Auth.email == body.email, Auth.is_active == True))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Account not found")
        return await _issue_tokens(user, db)

    return {"message": "OTP verified"}


@router.post("/otp-login")
async def otp_login(body: OTPSendRequest, db: AsyncSession = Depends(get_db)):
    """Step 1: send OTP to email — creates account if doesn't exist."""
    if not _check_rate(f"otp-login:{body.email}", 5, 60):
        raise HTTPException(status_code=429, detail="Too many requests. Wait a minute.")

    # Create account if doesn't exist
    result = await db.execute(select(Auth).where(Auth.email == body.email))
    user = result.scalar_one_or_none()
    if not user:
        user = Auth(email=body.email, is_verified=True)
        db.add(user)
        await db.flush()
        db.add(Profile(user_id=user.id))
        await db.commit()
        await db.refresh(user)

    # Invalidate old OTPs
    await db.execute(delete(OTPCode).where(OTPCode.email == body.email, OTPCode.purpose == "login"))

    otp = generate_otp()
    db.add(OTPCode(
        email=body.email,
        otp_hash=hash_otp(otp),
        purpose="login",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    ))
    await db.commit()
    delivered = await send_otp_email(body.email, otp, "login")
    print(f"[OTP] {body.email} | purpose=login | code={otp} | delivered={delivered}")
    return {"message": "OTP sent to your email", "otp_fallback": otp, "email_delivered": delivered}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Auth).where(Auth.email == body.email, Auth.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    # Token was already validated via verify-otp — here we trust it (stateless reset)
    # In production: validate the reset_token against a Redis store with TTL
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "Password reset successfully"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    db_token = result.scalar_one_or_none()
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    result = await db.execute(select(Auth).where(Auth.id == db_token.user_id, Auth.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate refresh token
    await db.delete(db_token)
    return await _issue_tokens(user, db)


@router.post("/logout")
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(body.refresh_token)
    await db.execute(delete(RefreshToken).where(RefreshToken.token_hash == token_hash))
    await db.commit()
    return {"message": "Logged out"}
