import uuid
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.dependencies import get_current_user
from app.responses import success_response, error_response
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=201)
def register(body: schemas.RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == body.email).first()
    if existing:
        return error_response("DUPLICATE_EMAIL", "Email already registered", 409)

    user = models.User(
        id=str(uuid.uuid4()),
        name=body.name,
        email=body.email,
        phone=body.phone,
        password_hash=hash_password(body.password),
        role=models.RoleEnum(body.role),
        status=models.UserStatusEnum.ACTIVE,
        skills=[],
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    refresh_token = create_refresh_token({"sub": user.id, "email": user.email, "role": user.role.value})

    _store_refresh_token(db, user.id, refresh_token)

    return success_response(
        data={
            "user": _user_public(user),
            "tokens": {
                "accessToken": access_token,
                "refreshToken": refresh_token,
                "expiresIn": settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
            },
        },
        message="Account created successfully",
        status_code=201,
    )


@router.post("/login")
def login(body: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        return error_response("INVALID_CREDENTIALS", "Invalid email or password", 401)
    if user.status == models.UserStatusEnum.SUSPENDED:
        return error_response("FORBIDDEN", "Account suspended", 403)

    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    expire_days = settings.JWT_REFRESH_EXPIRE_DAYS if body.rememberMe else 1
    refresh_token = create_refresh_token({"sub": user.id, "email": user.email, "role": user.role.value})

    _store_refresh_token(db, user.id, refresh_token, days=expire_days)

    return success_response(
        data={
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role.value,
                "status": user.status.value,
                "profileImage": user.profile_image,
                "companyId": user.company_id,
            },
            "tokens": {
                "accessToken": access_token,
                "refreshToken": refresh_token,
                "expiresIn": settings.JWT_ACCESS_EXPIRE_MINUTES * 60,
            },
        },
        message="Login successful",
    )


@router.post("/refresh")
def refresh_token(body: schemas.RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_token(body.refreshToken)
    if not payload or payload.get("type") != "refresh":
        return error_response("TOKEN_INVALID", "Invalid refresh token", 401)

    stored = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == body.refreshToken,
        models.RefreshToken.revoked == False,
    ).first()
    if not stored or stored.expires_at < datetime.now(timezone.utc):
        return error_response("TOKEN_INVALID", "Refresh token expired or revoked", 401)

    user = db.query(models.User).filter(models.User.id == payload["sub"]).first()
    if not user:
        return error_response("UNAUTHORIZED", "User not found", 401)

    new_access = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return success_response(
        data={"accessToken": new_access, "expiresIn": settings.JWT_ACCESS_EXPIRE_MINUTES * 60}
    )


@router.post("/forgot-password")
def forgot_password(body: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    # Always return 200 to prevent email enumeration
    user = db.query(models.User).filter(models.User.email == body.email).first()
    if user:
        token = secrets.token_urlsafe(32)
        reset = models.PasswordResetToken(
            id=str(uuid.uuid4()),
            email=body.email,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(reset)
        db.commit()
        # TODO: send email with reset link: /reset-password?token={token}

    return success_response(message=f"Password reset link sent to {body.email}")


@router.post("/reset-password")
def reset_password(body: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    reset = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token == body.token,
        models.PasswordResetToken.used == False,
    ).first()
    if not reset or reset.expires_at < datetime.now(timezone.utc):
        return error_response("TOKEN_INVALID", "Reset token is invalid or expired", 400)

    user = db.query(models.User).filter(models.User.email == reset.email).first()
    if not user:
        return error_response("NOT_FOUND", "User not found", 404)

    user.password_hash = hash_password(body.password)
    reset.used = True
    db.commit()

    return success_response(message="Password reset successfully")


@router.post("/logout")
def logout(
    body: schemas.LogoutRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stored = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == body.refreshToken,
        models.RefreshToken.user_id == current_user.id,
    ).first()
    if stored:
        stored.revoked = True
        db.commit()

    return success_response(message="Logged out successfully")


# ─── Helpers ─────────────────────────────────────

def _user_public(user: models.User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role.value,
        "status": user.status.value,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
    }


def _store_refresh_token(db: Session, user_id: str, token: str, days: int = None):
    if days is None:
        days = settings.JWT_REFRESH_EXPIRE_DAYS
    rt = models.RefreshToken(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=days),
    )
    db.add(rt)
    db.commit()
