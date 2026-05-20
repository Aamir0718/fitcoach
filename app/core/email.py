import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings


def _otp_html(otp: str, purpose: str) -> str:
    titles = {"verify": "Email Verification", "login": "Login OTP", "reset": "Password Reset"}
    title = titles.get(purpose, "Your OTP")
    return f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:480px;margin:auto;background:#0f0f1a;padding:40px;border-radius:16px;">
      <h1 style="color:#a78bfa;text-align:center;margin-bottom:8px;">⚡ FitCoach AI</h1>
      <p style="color:#94a3b8;text-align:center;margin-top:0;">{title}</p>
      <div style="background:#14141f;border-radius:12px;padding:32px;text-align:center;margin:24px 0;">
        <div style="font-size:48px;font-weight:900;color:#a78bfa;letter-spacing:12px;">{otp}</div>
        <p style="color:#64748b;font-size:13px;margin-top:16px;">Valid for 10 minutes</p>
      </div>
      <p style="color:#475569;font-size:12px;text-align:center;">
        If you didn't request this, ignore this email.
      </p>
    </div>
    """


async def send_otp_email(to_email: str, otp: str, purpose: str) -> bool:
    if not settings.SMTP_USER:
        # Dev mode — just print
        print(f"[DEV EMAIL] OTP for {to_email} ({purpose}): {otp}")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"FitCoach — Your OTP: {otp}"
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email

    msg.attach(MIMEText(_otp_html(otp, purpose), "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASS,
            start_tls=True,
        )
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send OTP to {to_email}: {e}")
        return False
