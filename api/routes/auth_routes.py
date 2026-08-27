"""Auth routes: login, OTP, refresh, logout, password reset, email verification."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import (
    blacklist_token,
    create_access_token,
    get_current_user,
)
from api.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshResponse,
    ResetPasswordRequest,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from database.db_session import get_session
from database.models import User
from utils.time import utc_now

router = APIRouter(tags=["Auth"])


@router.post(
    "/auth/login",
    summary="Authenticate and receive OTP",
    description="Authenticate with username and password. Returns user_id and role. "
    "A one-time password (OTP) is sent via email. The OTP MUST be verified at "
    "`/v1/auth/verify-otp` before a JWT token is issued.",
    response_description="OTP request confirmation with user_id (NO JWT - OTP verification required)",
)
def login(req: LoginRequest) -> dict:
    from services.auth_service import AuthError, AuthService

    with get_session() as session:
        auth_svc = AuthService(session)
        try:
            result = auth_svc.login(req.username, req.password)
        except AuthError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

        return {
            "status": "otp_required",
            "user_id": result["user_id"],
            "role": result["role"],
            "message": "OTP sent. Please verify at /v1/auth/verify-otp",
        }


@router.post(
    "/auth/verify-otp",
    response_model=VerifyOtpResponse,
    summary="Verify OTP and get JWT",
    description="Submit the OTP received via email to complete authentication. Returns a JWT access token.",
    response_description="JWT access token with user details",
)
def verify_otp(req: VerifyOtpRequest) -> bool:
    from services.auth_service import AuthError, AuthService

    with get_session() as session:
        auth_svc = AuthService(session)
        try:
            result = auth_svc.verify_otp(req.user_id, req.otp)
        except AuthError as e:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

        user_data = result["user"]
        token = create_access_token(
            {
                "sub": user_data["username"],
                "role": user_data["role"],
                "user_id": user_data["id"],
            }
        )
        return {
            "access_token": token,
            "role": user_data["role"],
            "user": user_data,
        }


@router.post(
    "/auth/refresh",
    response_model=RefreshResponse,
    summary="Refresh JWT token",
    description="Issue a new JWT using an existing valid Bearer token. "
    "The old token's JTI is blacklisted.",
    response_description="New JWT access token (old token is invalidated)",
)
def refresh_token(user: dict = Depends(get_current_user)) -> dict:
    expires_at = (
        datetime.fromtimestamp(user["exp"], tz=timezone.utc)
        if user.get("exp")
        else (utc_now() + timedelta(hours=24))
    )
    blacklist_token(user["jti"], expires_at, user["user_id"])

    token = create_access_token(
        {"sub": user["username"], "role": user["role"], "user_id": user["user_id"]}
    )
    return {"access_token": token}


@router.post(
    "/auth/verify-email/send",
    summary="Send/resend email verification",
    description="Generate and send a new email verification token. The token is valid for 24 hours.",
    response_description="Verification email confirmation",
)
def send_verification_email(req: VerifyOtpRequest) -> dict:
    from services.auth_service import AuthError, AuthService

    with get_session() as session:
        user = session.query(User).filter(User.id == req.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.email_verified:
            return {"status": "already_verified", "message": "Email is already verified."}

        auth_svc = AuthService(session)
        try:
            auth_svc.send_verification_email(user)
        except AuthError as e:
            raise HTTPException(status_code=400, detail=str(e))

        return {"status": "sent", "message": "Verification email sent. Check your inbox."}


@router.post(
    "/auth/verify-email/confirm",
    summary="Confirm email verification with token",
    description="Submit the verification token received via email to confirm your account.",
    response_description="Verification confirmation",
)
def confirm_verification(req: VerifyOtpRequest) -> dict:
    from services.auth_service import AuthError, AuthService

    with get_session() as session:
        auth_svc = AuthService(session)
        try:
            auth_svc.verify_email_token(req.user_id, req.otp)
        except AuthError as e:
            raise HTTPException(status_code=401, detail=str(e))

        return {"status": "verified", "message": "Email verified successfully. You can now log in."}


@router.post(
    "/auth/logout",
    summary="Logout and invalidate token",
    description="Invalidate the current JWT token.",
    response_description="Confirmation message with blacklist status",
)
def logout(user: dict = Depends(get_current_user)) -> dict:
    expires_at = (
        datetime.fromtimestamp(user["exp"], tz=timezone.utc)
        if user.get("exp")
        else (utc_now() + timedelta(hours=1))
    )
    blacklist_token(user["jti"], expires_at, user["user_id"])
    return {"status": "success", "message": "Token blacklisted. Successfully signed out."}


@router.post(
    "/auth/forgot-password",
    summary="Request password reset",
    description="Send a password reset link to the user's email. Always returns 200 to prevent user enumeration.",
    response_description="Generic confirmation message",
)
def forgot_password(req: ForgotPasswordRequest) -> dict:
    from services.auth_service import AuthService

    with get_session() as session:
        user = session.query(User).filter(User.email == req.email).first()
        if user:
            auth_svc = AuthService(session)
            try:
                auth_svc.send_password_reset_email(user)
            except (OSError, ValueError):
                pass  # Email failure must not leak whether the account exists

        return {
            "status": "sent",
            "message": "If an account with that email exists, a password reset link has been sent.",
        }


@router.post(
    "/auth/reset-password",
    summary="Reset password with token",
    description="Submit the password reset token and new password to complete the reset.",
    response_description="Reset confirmation",
)
def reset_password(req: ResetPasswordRequest) -> dict:
    from services.auth_service import AuthError, AuthService

    with get_session() as session:
        auth_svc = AuthService(session)
        try:
            auth_svc.reset_password(req.user_id, req.token, req.new_password)
            auth_svc.invalidate_user_sessions(req.user_id)
        except AuthError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except (ValueError, OSError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"An error occurred while resetting the password: {e}",
            )

        return {
            "status": "reset",
            "message": "Password reset successfully. You can now log in with your new password.",
        }
