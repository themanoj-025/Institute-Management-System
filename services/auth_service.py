"""
Unified authentication service.

OTP is generated, hashed, and stored server-side only using the ``otp_codes``
database table. The OTP code is NEVER returned in any response — it is sent
via email or printed to console in development mode.

verify_otp() compares against the server-side store, never against a
caller-supplied value. Brute-force protection: max 5 verify attempts per OTP.

Email Verification
------------------
New accounts start with ``email_verified=False``. The ``login()`` method
rejects login attempts from unverified accounts with a specific error message.
Verification tokens are SHA-256 hashed, single-use, and expire after 24 hours.
"""

import hashlib
import logging
import secrets
import smtplib
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import bcrypt
from sqlalchemy.orm import Session

from config.settings import (
    EMAIL_ENABLED,
    IS_DEV,
    LOCKOUT_TIME_MINUTES,
    MAX_LOGIN_ATTEMPTS,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USER,
)
from database.models import ActivityLog, EmailVerificationToken, OtpCode, User
from utils.time import utc_now

logger = logging.getLogger("auth")

# Password Reset Constants

RESET_TOKEN_TTL_MINUTES = 30  # 30-minute TTL
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

# Constants

OTP_TTL_SECONDS = 300  # 5 minutes
OTP_MAX_ATTEMPTS = 5
OTP_MAX_REQUESTS_PER_WINDOW = 3  # max 3 OTP requests per 10 minutes
OTP_RATE_LIMIT_WINDOW_SECONDS = 600  # 10 minutes

VERIFICATION_TOKEN_TTL_HOURS = 24
VERIFICATION_BASE_URL = "http://localhost:8000/v1/auth"


def _hash_otp(otp: str) -> str:
    """Hash OTP with SHA-256 for server-side storage."""
    return hashlib.sha256(otp.encode()).hexdigest()


def _cleanup_expired_otps(session: Session) -> None:
    """Remove expired OTPs from the database."""
    now = utc_now()
    session.query(OtpCode).filter(
        OtpCode.expires_at < now,
        OtpCode.is_used == False,
    ).delete()
    session.commit()


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Password Reset ─────────────────────────────────────────────

    def generate_password_reset_token(self, user_id: int) -> str:
        """Generate a password reset token, store its hash, return raw token.

        The raw token is returned so callers can include it in the
        reset email. Only the hash is stored in the database.
        Token expires after ``RESET_TOKEN_TTL_MINUTES`` (default 30).
        """
        from database.models import PasswordResetToken

        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)
        now = utc_now()
        entry = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=now + timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
            used_at=None,
            created_at=now,
        )
        self.db.add(entry)
        self.db.commit()
        return raw_token

    def verify_password_reset_token(self, user_id: int, raw_token: str) -> bool:
        """Verify a raw reset token against the stored hash.

        Single-use, TTL=30min. Marks token as used on success.
        Raises AuthError on failure.
        """
        from database.models import PasswordResetToken

        token_hash = self._hash_token(raw_token)
        now = utc_now()
        entry = (
            self.db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
            .order_by(PasswordResetToken.created_at.desc())
            .first()
        )
        if not entry:
            raise AuthError(
                "Password reset link is invalid or has expired. " "Request a new reset link."
            )
        # Single-use: mark as used
        entry.used_at = now
        self.db.commit()
        return True

    def send_password_reset_email(self, user: User) -> None:
        """Generate a reset token and send the password reset email."""
        raw_token = self.generate_password_reset_token(user.id)
        reset_link = (
            f"{VERIFICATION_BASE_URL}/reset-password/confirm"
            f"?user_id={user.id}&token={raw_token}"
        )
        if IS_DEV:
            logger.debug(
                "[DEV ONLY] Password reset link for %s: %s",
                user.username,
                reset_link,
            )
        elif EMAIL_ENABLED and user.email:
            self._send_reset_email_smtp(user.email, reset_link)

    def _send_reset_email_smtp(self, to_email: str, reset_link: str) -> None:
        """Send password reset email via SMTP."""
        try:
            msg = MIMEMultipart()
            msg["From"] = SMTP_USER
            msg["To"] = to_email
            msg["Subject"] = "BB-IMS: Password Reset Request"
            body = (
                f"You have requested a password reset for your BB-IMS account.\n\n"
                f"Click the link below to reset your password:\n\n"
                f"{reset_link}\n\n"
                f"This link is valid for {RESET_TOKEN_TTL_MINUTES} minutes.\n\n"
                f"If you did not request a password reset, please ignore this email.\n"
                f"Your current password remains unchanged."
            )
            msg.attach(MIMEText(body, "plain"))
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
            server.quit()
        except Exception as e:
            logger.error("Failed to send password reset email to %s: %s", to_email, e)

    @staticmethod
    def validate_password_strength(password: str) -> str:
        """Validate password meets the password policy.

        Returns the validated password if it meets requirements.
        Raises AuthError with a descriptive message if invalid.
        """
        if len(password) < PASSWORD_MIN_LENGTH:
            raise AuthError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.")
        if len(password) > PASSWORD_MAX_LENGTH:
            raise AuthError(f"Password must be at most {PASSWORD_MAX_LENGTH} characters long.")
        if not any(c.isupper() for c in password):
            raise AuthError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in password):
            raise AuthError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in password):
            raise AuthError("Password must contain at least one digit.")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for c in password):
            raise AuthError("Password must contain at least one special character.")
        return password

    def reset_password(self, user_id: int, raw_token: str, new_password: str) -> None:
        """Verify reset token and set new password.

        1. Verifies the reset token is valid, unexpired, and unused.
        2. Validates new password against the password policy.
        3. Hashes and sets the new password.
        4. Marks the token as used (single-use).
        5. Invalidates all active sessions (blacklists all JWTs).

        Raises AuthError on any failure.
        """
        # Verify token first
        self.verify_password_reset_token(user_id, raw_token)

        # Validate new password
        self.validate_password_strength(new_password)

        # Hash and set new password
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthError("User not found.")

        new_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt(14),
        ).decode("utf-8")
        user.password_hash = new_hash
        user.failed_login_attempts = 0
        user.locked_until = None
        user.password_changed_at = utc_now()
        self.db.commit()

        # Log the password reset activity
        log = ActivityLog(
            user_id=user.id,
            action="Password reset completed",
            module="Auth",
        )
        self.db.add(log)
        self.db.commit()

    def invalidate_user_sessions(self, user_id: int) -> None:
        """Invalidate all active sessions for a user.

        Sets ``password_changed_at`` on the user record to ``utc_now()``.
        The ``get_current_user()`` dependency checks this timestamp against
        the JWT's ``iat`` claim — any token issued before the password was
        changed is rejected.

        This is called after a password reset to ensure any stolen sessions
        are invalidated.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.password_changed_at = utc_now()
            self.db.commit()
            logger.info("Invalidated all sessions for user %d after password reset", user_id)

    # ── Email Verification ─────────────────────────────────────────

    def _hash_token(self, token: str) -> str:
        """Hash a token with SHA-256."""
        return hashlib.sha256(token.encode()).hexdigest()

    def generate_verification_token(self, user_id: int) -> str:
        """Generate a verification token, store its hash, return raw token.

        The raw token is returned so callers can include it in the
        verification email. Only the hash is stored in the database.
        """
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)
        now = utc_now()
        entry = EmailVerificationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=VERIFICATION_TOKEN_TTL_HOURS),
            is_used=False,
            created_at=now,
        )
        self.db.add(entry)
        self.db.commit()
        return raw_token

    def verify_email_token(self, user_id: int, raw_token: str) -> bool:
        """Verify a raw token against the stored hash.

        Single-use, TTL=24h. Marks user as verified on success.
        Raises AuthError on failure.
        """
        token_hash = self._hash_token(raw_token)
        entry = (
            self.db.query(EmailVerificationToken)
            .filter(
                EmailVerificationToken.user_id == user_id,
                EmailVerificationToken.token_hash == token_hash,
                EmailVerificationToken.is_used == False,
                EmailVerificationToken.expires_at > utc_now(),
            )
            .order_by(EmailVerificationToken.created_at.desc())
            .first()
        )
        if not entry:
            raise AuthError(
                "Verification link is invalid or has expired. " "Request a new verification email."
            )
        entry.is_used = True
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthError("User not found")
        user.email_verified = True
        self.db.commit()
        return True

    def send_verification_email(self, user: User) -> None:
        """Generate a verification token and send the verification email."""
        raw_token = self.generate_verification_token(user.id)
        verification_link = (
            f"{VERIFICATION_BASE_URL}/verify-email/confirm" f"?user_id={user.id}&token={raw_token}"
        )
        if IS_DEV:
            logger.debug(
                "[DEV ONLY] Verification link for %s: %s",
                user.username,
                verification_link,
            )
        elif EMAIL_ENABLED and user.email:
            self._send_verification_email_smtp(user.email, verification_link)

    def _send_verification_email_smtp(self, to_email: str, verification_link: str) -> None:
        """Send verification email via SMTP."""
        try:
            msg = MIMEMultipart()
            msg["From"] = SMTP_USER
            msg["To"] = to_email
            msg["Subject"] = "BB-IMS: Verify your account email"
            body = (
                f"Welcome to Binary Brain Institute Management System!\n\n"
                f"Please verify your email address by clicking the link below:\n\n"
                f"{verification_link}\n\n"
                f"This link is valid for {VERIFICATION_TOKEN_TTL_HOURS} hours.\n\n"
                f"If you did not create an account, please ignore this email."
            )
            msg.attach(MIMEText(body, "plain"))
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
            server.quit()
        except Exception as e:
            logger.error("Failed to send verification email to %s: %s", to_email, e)

    # ── OTP Rate Limiting ──────────────────────────────────────────

    def _check_otp_rate_limit(self, user_id: int) -> None:
        """Check if the user has exceeded the OTP request rate limit.

        Max ``OTP_MAX_REQUESTS_PER_WINDOW`` requests per
        ``OTP_RATE_LIMIT_WINDOW_SECONDS`` per user.
        """
        cutoff = utc_now() - timedelta(seconds=OTP_RATE_LIMIT_WINDOW_SECONDS)
        recent_count = (
            self.db.query(OtpCode)
            .filter(
                OtpCode.user_id == user_id,
                OtpCode.created_at >= cutoff,
            )
            .count()
        )
        if recent_count >= OTP_MAX_REQUESTS_PER_WINDOW:
            raise AuthError(
                f"OTP rate limit exceeded. Maximum {OTP_MAX_REQUESTS_PER_WINDOW} "
                f"requests per {OTP_RATE_LIMIT_WINDOW_SECONDS // 60} minutes."
            )

    # ── Login ──────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> dict:
        """Authenticate credentials and send OTP.

        Checks email verification before proceeding.
        Returns user_id and role only. The OTP is NEVER in the response.
        """
        user = self.db.query(User).filter(User.username == username).first()
        if not user:
            raise AuthError("Invalid username or password")

        # Check email verification
        if not user.email_verified:
            raise AuthError(
                "Please verify your email address before logging in. "
                "Check your inbox for the verification link."
            )

        if user.locked_until:
            # SQLite stores naive datetime even with DateTime(timezone=True).
            # Normalize both sides to naive for safe comparison.
            locked_until = user.locked_until.replace(tzinfo=None)
            now = utc_now().replace(tzinfo=None)
            if locked_until > now:
                remaining = int((locked_until - now).total_seconds() / 60)
                raise AuthError(f"Account locked. Try again in {remaining} minutes.")

        if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = utc_now() + timedelta(minutes=LOCKOUT_TIME_MINUTES)
            self.db.commit()
            raise AuthError("Invalid username or password")

        # Success — reset attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        self.db.commit()

        # Rate limit check before generating OTP
        self._check_otp_rate_limit(user.id)

        # Generate 6-digit OTP
        otp_code = f"{secrets.randbelow(900000) + 100000}"

        # Store hashed OTP in database with TTL
        _cleanup_expired_otps(self.db)
        now = utc_now()
        otp_entry = OtpCode(
            user_id=user.id,
            code_hash=_hash_otp(otp_code),
            expires_at=now + timedelta(seconds=OTP_TTL_SECONDS),
            max_attempts=OTP_MAX_ATTEMPTS,
            is_used=False,
            created_at=now,
        )
        self.db.add(otp_entry)
        self.db.commit()

        # Send OTP via email or log in dev — OTP is NEVER returned in response
        if IS_DEV:
            logger.debug(f"[DEV ONLY] OTP for {username}: {otp_code}")
        elif EMAIL_ENABLED and user.email:
            self._send_otp_email(user.email, otp_code)

        return {
            "user_id": user.id,
            "role": user.role.value,
            "otp_sent": True,
            "message": "OTP sent. Check your email for the verification code.",
        }

    def _send_otp_email(self, to_email: str, otp_code: str) -> None:
        """Send OTP via SMTP. Failures are logged but do not block login."""
        try:
            msg = MIMEMultipart()
            msg["From"] = SMTP_USER
            msg["To"] = to_email
            msg["Subject"] = "Your BB-IMS Login OTP"
            body = f"Your OTP for login is: {otp_code}. It is valid for 5 minutes."
            msg.attach(MIMEText(body, "plain"))
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
            server.quit()
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")

    def verify_otp(self, user_id: int, submitted_otp: str) -> dict:
        """Verify OTP against server-side database store.

        - Never compares against a caller-supplied value.
        - Enforces expiry (TTL: 5 minutes).
        - Enforces max 5 verify attempts before invalidation.
        - Single-use: deletes code on successful verification.

        Raises ``AuthError`` on failure.
        """
        _cleanup_expired_otps(self.db)

        # Fetch the most recent unused OTP for this user
        otp_entry = (
            self.db.query(OtpCode)
            .filter(
                OtpCode.user_id == user_id,
                OtpCode.is_used == False,
                OtpCode.expires_at > utc_now(),
            )
            .order_by(OtpCode.created_at.desc())
            .first()
        )

        if not otp_entry:
            raise AuthError("OTP expired or not found. Please login again.")

        # Increment attempt counter
        otp_entry.attempt_count += 1
        self.db.commit()

        # Check max attempts
        if otp_entry.attempt_count > otp_entry.max_attempts:
            otp_entry.is_used = True
            self.db.commit()
            raise AuthError("OTP invalidated due to too many failed attempts. Please login again.")

        # Verify hash
        if _hash_otp(submitted_otp) != otp_entry.code_hash:
            raise AuthError("Invalid OTP")

        # Valid — mark as used (single-use)
        otp_entry.is_used = True
        self.db.commit()

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise AuthError("User not found")

        # Log activity
        log = ActivityLog(user_id=user.id, action="Login successful", module="Auth")
        self.db.add(log)
        self.db.commit()

        user_data = {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "email": user.email,
        }

        # Add profile names
        if user.role.value == "staff" and user.staff_profile:
            user_data["name"] = f"{user.staff_profile.first_name} {user.staff_profile.last_name}"
            user_data["profile_id"] = user.staff_profile.id
        elif user.role.value == "student" and user.student_profile:
            user_data["name"] = (
                f"{user.student_profile.first_name} {user.student_profile.last_name}"
            )
            user_data["profile_id"] = user.student_profile.id
        else:
            user_data["name"] = "Administrator"

        return {"user": user_data}
