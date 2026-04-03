"""
Email utility — Gmail SMTP.
LOCAL DEV : OTP printed to terminal + returned in API response (shown on screen).
PRODUCTION: OTP sent to user's real email via Gmail SMTP.

To enable on Azure:
  set FLASK_ENV=production
  set MAIL_USERNAME=yourgmail@gmail.com
  set MAIL_PASSWORD=your-app-password   (Gmail App Password, not your login password)
"""
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(to_email, otp_code, user_name='there'):
    """
    Sends OTP email.
    Returns (success: bool, message: str)
    """
    app = current_app._get_current_object()
    dev_mode = app.config.get('DEV_MODE', True)

    # ── LOCAL DEV ─────────────────────────────────────────
    if dev_mode:
        print(f"\n{'='*50}")
        print(f"[Cloud Bridge] OTP SIMULATION (Dev Mode)")
        print(f"  To      : {to_email}")
        print(f"  OTP Code: {otp_code}")
        print(f"  (On Azure this will be sent as a real email)")
        print(f"{'='*50}\n")
        return True, 'dev'

    # ── PRODUCTION (Azure/GCP) ────────────────────────────
    username = app.config.get('MAIL_USERNAME')
    password = app.config.get('MAIL_PASSWORD')
    if not username or not password:
        print(f"[Cloud Bridge] WARNING: MAIL_USERNAME/MAIL_PASSWORD not set. OTP={otp_code}")
        return False, 'Email credentials not configured'

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '🔐 Your Cloud Bridge OTP Code'
        msg['From']    = f"Cloud Bridge <{username}>"
        msg['To']      = to_email

        html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;">
          <div style="text-align:center;margin-bottom:24px;">
            <div style="background:#1A6B5A;width:48px;height:48px;border-radius:12px;
                        display:inline-flex;align-items:center;justify-content:center;
                        font-size:24px;">📁</div>
            <h2 style="color:#1C1C1C;margin:12px 0 0;">Cloud Bridge</h2>
          </div>
          <h3 style="color:#1C1C1C;">Hi {user_name},</h3>
          <p style="color:#5A5A5A;">Use this OTP to verify your email and create your account:</p>
          <div style="background:#E8F4F1;border:2px solid #1A6B5A;border-radius:12px;
                      padding:24px;text-align:center;margin:24px 0;">
            <div style="font-size:36px;font-weight:700;letter-spacing:12px;color:#1A6B5A;">{otp_code}</div>
          </div>
          <p style="color:#9A9A9A;font-size:13px;">This OTP expires in 10 minutes. Do not share it with anyone.</p>
          <hr style="border:none;border-top:1px solid #E0D9CE;margin:24px 0;"/>
          <p style="color:#9A9A9A;font-size:12px;text-align:center;">Cloud Bridge — Smart File Management</p>
        </div>
        """

        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.ehlo()
            server.starttls()
            server.login(username, password)
            server.sendmail(username, to_email, msg.as_string())

        print(f"LOG: OTP email sent to {to_email}")
        return True, 'sent'

    except Exception as e:
        print(f"LOG: Email send failed → {str(e)}")
        return False, str(e)


def send_upload_notification(to_email, filename, user_name='there'):
    """Sends file upload confirmation email."""
    app = current_app._get_current_object()
    dev_mode = app.config.get('DEV_MODE', True)

    print(f"EVENT: File uploaded → {filename}")
    print(f"process_event() → Processing upload for {to_email}")

    if dev_mode:
        print(f"[Cloud Bridge] NOTIFICATION SIMULATION: Upload email to {to_email} for {filename}")
        return

    username = app.config.get('MAIL_USERNAME')
    password = app.config.get('MAIL_PASSWORD')
    if not username or not password:
        return

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'✅ File Uploaded — {filename}'
        msg['From']    = f"Cloud Bridge <{username}>"
        msg['To']      = to_email

        html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px;">
          <h3>Hi {user_name},</h3>
          <p>Your file <strong>{filename}</strong> has been uploaded successfully to Cloud Bridge.</p>
          <p style="color:#9A9A9A;font-size:13px;">Cloud Bridge — Smart File Management</p>
        </div>
        """
        msg.attach(MIMEText(html, 'html'))
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.ehlo(); server.starttls()
            server.login(username, password)
            server.sendmail(username, to_email, msg.as_string())
    except Exception as e:
        print(f"LOG: Upload notification failed → {str(e)}")
