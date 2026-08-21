"""
Email notification service.

SMTP credentials are loaded from environment variables (SMTP_HOST, SMTP_PORT,
SMTP_USER, SMTP_PASSWORD) — never from config files.
"""

import os
import smtplib
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailNotifier:
    def __init__(self) -> None:
        """Load SMTP configuration from environment variables."""
        self.smtp_host = os.getenv("SMTP_HOST", "")
        try:
            self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        except (ValueError, TypeError):
            self.smtp_port = 587
        self.sender = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")

    def send_email(self, to_email: str, subject: str, body_html: str) -> None:
        """Send an email asynchronously. Fails silently if SMTP not configured."""
        if not self.sender or not self.password:
            print("Email not configured (SMTP_USER/SMTP_PASSWORD missing). Skipping email send.")
            return

        def task() -> None:
            try:
                msg = MIMEMultipart()
                msg["From"] = self.sender
                msg["To"] = to_email
                msg["Subject"] = subject
                msg.attach(MIMEText(body_html, "html"))

                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
                server.login(self.sender, self.password)
                server.send_message(msg)
                server.quit()
                print(f"Email sent to {to_email}")
            except Exception as e:
                print(f"Failed to send email to {to_email}: {e}")

        threading.Thread(target=task, daemon=True).start()


email_notifier = EmailNotifier()
