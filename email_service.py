import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from config import settings


class EmailService:
    """Service for sending transactional emails such as password reset."""

    def __init__(self):
        self.host = settings.EMAIL_HOST
        self.port = settings.EMAIL_PORT
        self.use_tls = settings.EMAIL_USE_TLS
        self.username = settings.EMAIL_USERNAME
        self.password = settings.EMAIL_PASSWORD
        self.from_email = settings.EMAIL_FROM or self.username
        self.from_name = settings.EMAIL_FROM_NAME or "Sokoni Africa"

    def send_password_reset_code(self, to_email: str, code: str) -> bool:
        """Send a password reset code to the user's email address."""
        subject = "Reset your Sokoni Africa password"
        body = self._build_reset_email_body(code)
        return self._send_email(to_email, subject, body)

    def _build_reset_email_body(self, code: str) -> str:
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #1f2937;">
                <div style="max-width: 480px; margin: 0 auto; padding: 24px;">
                    <h2 style="color: #0a4b78;">Password Reset Request</h2>
                    <p>Hello,</p>
                    <p>We received a request to reset your Sokoni Africa password. Use the verification code below to complete the reset in the app:</p>
                    <p style="
                        font-size: 28px;
                        font-weight: bold;
                        letter-spacing: 8px;
                        text-align: center;
                        padding: 12px 16px;
                        background-color: #f1f5f9;
                        border-radius: 12px;
                        color: #0a4b78;
                        border: 1px solid #cbd5f5;
                    ">
                        {code}
                    </p>
                    <p>This code will expire in 10 minutes. If you did not request a password reset, you can safely ignore this email.</p>
                    <p style="margin-top: 32px;">Best regards,<br><strong>{self.from_name}</strong><br>Sokoni Africa Support</p>
                </div>
            </body>
        </html>
        """

    def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            message.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.host, self.port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_email, to_email, message.as_string())
            return True
        except Exception as exc:
            print(f"❌ Error sending email to {to_email}: {exc}")
            return False

