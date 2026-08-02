"""
Email sending — tries Brevo first (verified single sender, no domain needed),
then Resend, then SMTP. In dev mode (no keys set) prints OTP to console/logs.
"""
import aiosmtplib
import httpx
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings


def _otp_html(otp: str, purpose: str) -> str:
    titles = {"verify": "Email Verification", "login": "Login Code", "reset": "Password Reset"}
    title = titles.get(purpose, "Your Code")
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#08080f;font-family:Inter,Arial,sans-serif;">
<div style="max-width:480px;margin:40px auto;background:#111118;border-radius:20px;overflow:hidden;border:1px solid #1e1e30;">
  <div style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);padding:32px;text-align:center;">
    <div style="font-size:36px;margin-bottom:8px;">⚡</div>
    <h1 style="color:white;margin:0;font-size:24px;font-weight:900;letter-spacing:-0.5px;">FitCoach AI</h1>
    <p style="color:rgba(255,255,255,0.7);margin:8px 0 0;font-size:14px;">{title}</p>
  </div>
  <div style="padding:40px 32px;text-align:center;">
    <p style="color:#94a3b8;margin:0 0 24px;font-size:15px;line-height:1.6;">
      Here is your verification code:
    </p>
    <div style="background:#08080f;border:1px solid #1e1e30;border-radius:16px;padding:28px;margin:0 auto 24px;">
      <div style="font-size:52px;font-weight:900;color:#8b5cf6;letter-spacing:14px;font-family:monospace;">{otp}</div>
      <p style="color:#475569;font-size:13px;margin:14px 0 0;">Valid for 10 minutes</p>
    </div>
    <p style="color:#475569;font-size:12px;margin:0;line-height:1.6;">
      If you didn't request this code, you can safely ignore this email.<br>
      Your account is secure.
    </p>
  </div>
  <div style="background:#0a0a12;padding:20px 32px;text-align:center;border-top:1px solid #1e1e30;">
    <p style="color:#334155;font-size:11px;margin:0;">© 2026 FitCoach AI · AI-Powered Fitness Coaching</p>
  </div>
</div>
</body>
</html>"""


async def send_otp_email(to_email: str, otp: str, purpose: str) -> bool:
    """Send OTP email. Tries Brevo → Resend → SMTP → dev-mode log."""
    subject = f"FitCoach AI — Your code: {otp}"
    html = _otp_html(otp, purpose)

    # ── Brevo (verified single sender, no domain needed — preferred) ──────────
    if settings.BREVO_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.brevo.com/v3/smtp/email",
                    headers={"api-key": settings.BREVO_API_KEY, "Content-Type": "application/json"},
                    json={
                        "sender": {"name": "FitCoach AI", "email": "infoatfitcoachai@gmail.com"},
                        "to": [{"email": to_email}],
                        "subject": subject,
                        "htmlContent": html,
                    },
                )
            if resp.status_code in (200, 201):
                print(f"[Brevo] OTP sent to {to_email} ({purpose})")
                return True
            print(f"[Brevo ERROR] {resp.status_code} {resp.text} — falling back")
        except Exception as e:
            print(f"[Brevo ERROR] {e} — falling back")

    # ── Resend (preferred for cloud deployments) ──────────────────────────────
    if settings.RESEND_API_KEY:
        try:
            import resend
            resend.api_key = settings.RESEND_API_KEY
            params = {
                "from": settings.EMAIL_FROM or "FitCoach AI <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "html": html,
            }
            resend.Emails.send(params)
            print(f"[Resend] OTP sent to {to_email} ({purpose})")
            return True
        except Exception as e:
            print(f"[Resend ERROR] {e} — falling back to SMTP")

    # ── Gmail SMTP fallback ───────────────────────────────────────────────────
    if settings.SMTP_USER:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = settings.EMAIL_FROM
        msg["To"]      = to_email
        msg.attach(MIMEText(html, "html"))
        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASS.replace(" ", ""),  # strip spaces from app password
                start_tls=True,
                timeout=15,
            )
            print(f"[SMTP] OTP sent to {to_email} ({purpose})")
            return True
        except Exception as e:
            print(f"[SMTP ERROR] Failed to send OTP to {to_email}: {e}")
            # Fall through to dev-mode log so OTP can be read from Render logs
            print(f"[FALLBACK OTP] {to_email} ({purpose}): {otp}")
            return False

    # ── Dev mode — no email config ────────────────────────────────────────────
    print(f"[DEV EMAIL] OTP for {to_email} ({purpose}): {otp}")
    return True
