import smtplib
import os
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ==========================================================
# COMMON EMAIL SENDER (WITH CID LOGO SUPPORT)
# ==========================================================

def _send_email_html(
    to_email: str,
    subject: str,
    body_html: str,
    payops_logo_data: bytes = None,
    company_logo_data: bytes = None,
):

    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

    if not SMTP_SERVER or not SENDER_EMAIL or not SENDER_PASSWORD:
        logger.error("Email configuration missing")
        raise Exception("SMTP configuration missing")

    try:
        msg = MIMEMultipart("related")

        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)

        msg_alternative.attach(MIMEText(body_html, "html"))

        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject

        #msg.attach(MIMEText(body_html, "html"))

        # 🔹 PayOps Logo (static → convert to bytes)
        if payops_logo_data:
            img = MIMEImage(payops_logo_data, _subtype="png")  # or "jpeg"
            img.add_header("Content-ID", "<payops_logo>")
            img.add_header("Content-Disposition", "inline", filename="payops_logo.png")
            msg.attach(img)

        # 🔹 Company Logo (dynamic from DB/API)
        if company_logo_data:
            img = MIMEImage(company_logo_data, _subtype="png")
            img.add_header("Content-ID", "<company_logo>")
            img.add_header("Content-Disposition", "inline", filename="company_logo.png")
            msg.attach(img)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()

        logger.info(f"Email sent successfully to {to_email}")

    except Exception:
        logger.exception(f"Failed to send email to {to_email}")
        raise


# ==========================================================
# COMPANY ACTIVATION EMAIL
# ==========================================================

def send_activation_email(
    to_email: str,
    company_name: str,
    schema_id: str,
    admin_email: str,
    temp_password: str,
    company_logo_data: bytes = None,   # 👈 from DB
):

    subject = f"🎉 Welcome to PayOps - {company_name}"

    # 🔹 Load PayOps logo (static file → bytes)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    payops_logo_path = os.path.join(base_dir, "static", "common", "payops_logo.png")

    payops_logo_data = None
    if os.path.exists(payops_logo_path):
        with open(payops_logo_path, "rb") as f:
            payops_logo_data = f.read()

    # ==========================================================
    # HTML TEMPLATE 
    # ==========================================================

    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='UTF-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    </head>

    <body style="font-family: Arial; background:#f4f4f4; margin:0; padding:0;">

        <table width="100%" style="padding:40px 0;">
            <tr>
                <td align="center">

                    <table width="600" style="background:#ffffff; border-radius:12px; border:1px solid #e0e0e0;">

                        <!-- HEADER -->
                        <tr>
                            <td style="background:#153A7B; padding:20px; border-radius:12px 12px 0 0;">

                                <table width="100%">
                                    <tr>
                                        <td align="left">
                                            <img src="https://raw.githubusercontent.com/shruthi-mgit/PayOpsB1logo/main/PayOps%20B1.png" width="160"/>
                                        </td>

                                        <td align="right">
                                            {"<img src='cid:company_logo' width='160'/>" if company_logo_data else ""}
                                        </td>
                                    </tr>
                                </table>

                                <h2 style="color:white; text-align:center; margin-top:20px;">
                                    🚀 Welcome to PayOpsB1
                                </h2>
                            </td>
                        </tr>

                        <!-- BODY -->
                        <tr>
                            <td style="padding:30px;">

                                <h3 style="color:#153A7B;">Company Activated</h3>

                                <p>Dear <b>{company_name}</b>,</p>

                                <p>Your company has been successfully activated.</p>

                                <table width="100%" style="background:#eef5ff; padding:15px;
                                       border-left:4px solid #153A7B; margin:20px 0;">
                                    <tr>
                                        <td>
                                            <b>Schema:</b> {schema_id}<br>
                                            <b>Admin Email:</b> {admin_email}<br>
                                            <b>Password:</b> {temp_password}
                                        </td>
                                    </tr>
                                </table>

                                <p style="color:red;">⚠️ Please change your password after login.</p>

                                <div style="text-align:center; margin:30px 0;">
                                    <a href="https://your-payops-login-url"
                                       style="background:#153A7B; color:white; padding:12px 30px;
                                              text-decoration:none; border-radius:6px;">
                                        🔐 Login to PayOpsB1
                                    </a>
                                </div>

                                <p>Regards,<br><b>PayOpsB1 Team</b></p>

                            </td>
                        </tr>

                        <!-- FOOTER -->
                        <tr>
                            <td style="background:#f6f7fb; text-align:center; padding:20px;
                                       font-size:12px; color:#777;">
                                © 2026 PayOpsB1. All rights reserved.
                            </td>
                        </tr>

                    </table>

                </td>
            </tr>
        </table>

    </body>
    </html>
    """

    # ==========================================================
    # SEND EMAIL
    # ==========================================================

    _send_email_html(
        to_email=to_email,
        subject=subject,
        body_html=body_html,
        payops_logo_data=payops_logo_data,
        company_logo_data=company_logo_data
    )