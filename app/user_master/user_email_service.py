import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# ==========================================================
# LOAD PAYOPS LOGO (COMMON)
# ==========================================================

def _load_payops_logo():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_dir, "static", "payops_logo.png")

    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            return f.read()
    return None


# ==========================================================
# COMMON EMAIL SENDER (TENANT SMTP)
# ==========================================================

def _send_email_html(
    to_email: str,
    subject: str,
    body_html: str,
    smtp_server: str,
    smtp_port: int,
    sender_email: str,
    sender_password: str,
):

    try:
        msg = MIMEMultipart("related")

        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body_html, "html"))

        # 🔹 Attach PayOps Logo
        logo_data = _load_payops_logo()
        if logo_data:
            img = MIMEImage(logo_data)
            img.add_header("Content-ID", "<payops_logo>")
            msg.attach(img)

        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        print("✅ Tenant email sent:", to_email)

    except Exception as e:
        print("❌ Tenant email error:", str(e))


# ==========================================================
# ENV SMTP EMAIL SENDER
# ==========================================================

def _send_env_email_html(to_email: str, subject: str, body_html: str):

    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    try:
        msg = MIMEMultipart("related")

        msg["From"] = sender_email
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body_html, "html"))

        # 🔹 Attach PayOps Logo
        logo_data = _load_payops_logo()
        if logo_data:
            img = MIMEImage(logo_data)
            img.add_header("Content-ID", "<payops_logo>")
            msg.attach(img)

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        print("✅ ENV email sent:", to_email)

    except Exception as e:
        print("❌ ENV email error:", str(e))


# ==========================================================
# USER ONBOARD EMAIL
# ==========================================================

def send_user_onboard_email(
    email: str,
    name: str,
    tenant_schema: str,
    temp_password: str,
    login_url: str,
    smtp_server: str = None,
    smtp_port: int = None,
    sender_email: str = None,
    sender_password: str = None,
):

    subject = "🎉 Welcome to PayOps"

    display_password = temp_password if temp_password else "Not Available"

    body_html = f"""
    <html>
    <body style="font-family: Arial; background:#f4f4f4; padding:20px;">
        <div style="max-width:600px; margin:auto; background:white; border-radius:10px; padding:20px;">
            
            <!-- LOGO -->
            <div style="text-align:center; margin-bottom:20px;">
                <img src="cid:payops_logo" width="140"/>
            </div>

            <h2 style="color:#153A7B;">Welcome to PayOps</h2>

            <p>Hello <b>{name}</b>,</p>

            <p>Your account has been created successfully.</p>

            <h3>🔐 Login Details</h3>
            <p><b>Tenant:</b> {tenant_schema}</p>
            <p><b>Email:</b> {email}</p>
            <p><b>Password:</b> {display_password}</p>

            <p style="color:red;">⚠️ Please change your password after first login.</p>

            <br>

            <a href="{login_url}" 
               style="background:#357ABD; color:white; padding:12px 20px; text-decoration:none; border-radius:5px;">
               🔐 Login Now
            </a>

            <br><br>

            <p>Regards,<br><b>PayOps Team</b></p>
        </div>
    </body>
    </html>
    """

    try:
        if smtp_server and sender_email:
            _send_email_html(
                email,
                subject,
                body_html,
                smtp_server,
                smtp_port,
                sender_email,
                sender_password,
            )
        else:
            _send_env_email_html(email, subject, body_html)

    except Exception as e:
        print("❌ Onboard email failed:", str(e))


# ==========================================================
# RESET OTP EMAIL
# ==========================================================

def send_reset_otp_email(to_email: str, otp: str):

    subject = "🔐 Password Reset OTP"

    body_html = f"""
    <html>
    <body style="font-family: Arial; background:#f4f4f4; padding:20px;">
        <div style="max-width:500px; margin:auto; background:white; border-radius:10px; padding:20px; text-align:center;">
            
            <!-- LOGO -->
            <div style="margin-bottom:20px;">
                <img src="cid:payops_logo" width="140"/>
            </div>

            <h2 style="color:#153A7B;">Password Reset</h2>

            <p>Your OTP is:</p>

            <div style="font-size:24px; font-weight:bold; color:#c2185b; margin:20px;">
                {otp}
            </div>

            <p>This OTP is valid for 10 minutes.</p>

            <p>If you didn’t request this, ignore this email.</p>

            <br>

            <p>Regards,<br><b>PayOps Team</b></p>
        </div>
    </body>
    </html>
    """

    _send_env_email_html(to_email, subject, body_html)