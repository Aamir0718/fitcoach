from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timezone, datetime

from app.database import get_db
from app.models.auth import Auth
from app.models.recovery import RecoveryLog
from app.schemas.recovery import RecoveryLogRequest, RecoveryResponse
from app.core.security import get_current_verified_user

router = APIRouter(prefix="/api/recovery", tags=["recovery"])


def calculate_recovery(req: RecoveryLogRequest) -> tuple[int, str]:
    sleep_score = min(5.0, max(1.0, (req.sleep_hours / 8.0) * 5))
    fatigue_inv  = 6 - req.fatigue
    soreness_inv = 6 - req.soreness
    load_inv     = 6 - req.prev_load

    # Weighted formula — coefficients sum to 100
    raw = (
        sleep_score   * 30 +
        req.sleep_quality * 20 +
        fatigue_inv   * 25 +
        soreness_inv  * 15 +
        load_inv      * 10
    )
    # Normalize: max possible raw = 5*30 + 5*20 + 5*25 + 5*15 + 5*10 = 500, scale to 100
    score = int(min(100, max(0, raw / 5.0)))
    zone  = "green" if score >= 80 else ("yellow" if score >= 60 else "red")
    return score, zone


@router.post("/", response_model=RecoveryResponse, status_code=201)
async def log_recovery(
    body: RecoveryLogRequest,
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    score, zone = calculate_recovery(body)

    log = RecoveryLog(
        user_id=current_user.id,
        date=date.today(),
        sleep_hours=body.sleep_hours,
        sleep_quality=body.sleep_quality,
        fatigue=body.fatigue,
        soreness=body.soreness,
        prev_load=body.prev_load,
        score=score,
        zone=zone,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@router.get("/latest", response_model=RecoveryResponse)
async def get_latest_recovery(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RecoveryLog)
        .where(RecoveryLog.user_id == current_user.id)
        .order_by(RecoveryLog.created_at.desc())
        .limit(1)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="No recovery data yet")
    return log


@router.get("/history", response_model=list[RecoveryResponse])
async def get_recovery_history(
    current_user: Auth = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 30,
):
    result = await db.execute(
        select(RecoveryLog)
        .where(RecoveryLog.user_id == current_user.id)
        .order_by(RecoveryLog.date.desc())
        .limit(limit)
    )
    return result.scalars().all()
