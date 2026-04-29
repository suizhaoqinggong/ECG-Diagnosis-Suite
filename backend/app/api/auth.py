from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.auth_dependencies import get_current_user
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.rate_limit import (
    check_delete_account_limit,
    check_login_limit,
    check_refresh_ip_limit,
    check_refresh_user_limit,
    check_register_limit,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    get_password_hash,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    display_name: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email address")
        local, domain = normalized.rsplit("@", 1)
        if not local or "." not in domain:
            raise ValueError("Invalid email address")
        return normalized


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Invalid email address")
        local, domain = normalized.rsplit("@", 1)
        if not local or "." not in domain:
            raise ValueError("Invalid email address")
        return normalized


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class DeleteAccountRequest(BaseModel):
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str | None

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    user: UserResponse


def _validate_origin(request: Request) -> None:
    """Validate Origin header for CSRF protection."""
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        return  # Allow if no origin (same-origin request)

    parsed = urlparse(origin)
    # Reject origins with malformed ports (e.g. http://localhost:5173.evil.com)
    try:
        parsed_port = parsed.port
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid origin",
        )
    # Normalize missing port to scheme default for consistent comparison
    if parsed_port is None:
        parsed_port = 443 if parsed.scheme == "https" else 80
    for allowed in settings.CORS_ORIGINS:
        allowed_parsed = urlparse(allowed)
        # When the allowed origin has no explicit port, bind to scheme default
        if allowed_parsed.port is None:
            default_port = 443 if allowed_parsed.scheme == "https" else 80
            if parsed_port != default_port:
                continue
        elif parsed_port != allowed_parsed.port:
            continue
        if (
            parsed.scheme == allowed_parsed.scheme
            and parsed.hostname == allowed_parsed.hostname
        ):
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid origin",
    )


def _set_refresh_cookie(response: Response, token_value: str) -> None:
    cookie_secure = not settings.DEBUG
    response.set_cookie(
        key="rt",
        value=token_value,
        httponly=True,
        secure=cookie_secure,
        samesite="lax",
        path="/api/auth",
        max_age=7 * 24 * 60 * 60,  # 7 days
    )


def _create_refresh_token_record(
    user_id: int, session: AsyncSessionLocal
) -> tuple[str, RefreshToken]:
    """Generate refresh token value and ORM object."""
    token_value = generate_refresh_token()
    token_hash = hashlib.sha256(token_value.encode()).hexdigest()
    family_id = hashlib.sha256(token_value.encode()).hexdigest()[:16]
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        family_id=family_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    return token_value, refresh_token


@router.post("/register", response_model=AuthResponse)
async def register(
    request: Request,
    response: Response,
    data: RegisterRequest,
) -> AuthResponse:
    """Register a new user."""
    _validate_origin(request)
    await check_register_limit(request, data.email)

    async with AsyncSessionLocal() as session:
        # Check if email exists
        result = await session.execute(
            select(User).where(User.email == data.email.lower())
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed",
            )

        # Create user
        user = User(
            email=data.email.lower(),
            hashed_password=get_password_hash(data.password),
            display_name=data.display_name,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Create refresh token
        token_value, refresh_token = _create_refresh_token_record(user.id, session)
        session.add(refresh_token)
        await session.commit()

        _set_refresh_cookie(response, token_value)

        access_token, _ = create_access_token(user.id)
        return AuthResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
) -> AuthResponse:
    """Login existing user."""
    _validate_origin(request)
    await check_login_limit(request, data.email)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == data.email.lower())
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Create refresh token
        token_value, refresh_token = _create_refresh_token_record(user.id, session)
        session.add(refresh_token)
        await session.commit()

        _set_refresh_cookie(response, token_value)

        access_token, _ = create_access_token(user.id)
        return AuthResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    rt: Annotated[str | None, Cookie()] = None,
) -> AuthResponse:
    """Refresh access token using refresh token cookie."""
    _validate_origin(request)
    await check_refresh_ip_limit(request)

    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    token_hash = hashlib.sha256(rt.encode()).hexdigest()
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .options(selectinload(RefreshToken.user))
        )
        token = result.scalar_one_or_none()

        if not token or token.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        await check_refresh_user_limit(token.user_id)

        # Check for replay attack
        if token.revoked_at:
            # Revoke entire family
            await session.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == token.family_id)
                .values(revoked_at=now)
            )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token reuse detected",
            )

        revoke_result = await session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token.id)
            .where(RefreshToken.revoked_at.is_(None))
            .where(RefreshToken.expires_at >= now)
            .values(revoked_at=now)
        )

        if revoke_result.rowcount != 1:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        # Rotate token
        new_token_value = generate_refresh_token()
        new_token_hash = hashlib.sha256(new_token_value.encode()).hexdigest()

        new_token = RefreshToken(
            user_id=token.user_id,
            token_hash=new_token_hash,
            family_id=token.family_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        session.add(new_token)
        await session.flush()

        # Mark old token as revoked
        token.replaced_by_id = new_token.id
        token.revoked_at = now
        await session.commit()

        _set_refresh_cookie(response, new_token_value)

        access_token, _ = create_access_token(token.user_id)
        return AuthResponse(
            access_token=access_token,
            user=UserResponse.model_validate(token.user),
        )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    rt: Annotated[str | None, Cookie()] = None,
) -> dict[str, str]:
    """Logout - revoke refresh token and clear cookie."""
    _validate_origin(request)

    if rt:
        token_hash = hashlib.sha256(rt.encode()).hexdigest()

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            )
            token = result.scalar_one_or_none()
            if token:
                token.revoked_at = datetime.now(timezone.utc)
                await session.commit()

    response.delete_cookie(key="rt", path="/api/auth")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Get current user info."""
    return current_user


@router.post("/change-password")
async def change_password(
    request: Request,
    response: Response,
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Change password - revokes all refresh tokens."""
    _validate_origin(request)

    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid old password",
        )

    async with AsyncSessionLocal() as session:
        # Re-attach user to this session
        result = await session.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one()
        user.hashed_password = get_password_hash(data.new_password)

        # Revoke all refresh tokens
        await session.execute(
            RefreshToken.__table__.update()
            .where(RefreshToken.user_id == current_user.id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await session.commit()

    response.delete_cookie(key="rt", path="/api/auth")
    return {"message": "Password changed"}


@router.post("/delete-account")
async def delete_account(
    request: Request,
    response: Response,
    data: DeleteAccountRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Delete user account and all associated data."""
    _validate_origin(request)
    await check_delete_account_limit(current_user.id)

    # Verify password before allowing account deletion
    if not verify_password(data.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one()
        await session.delete(user)
        await session.commit()

    response.delete_cookie(key="rt", path="/api/auth")
    return {"message": "Account deleted"}
