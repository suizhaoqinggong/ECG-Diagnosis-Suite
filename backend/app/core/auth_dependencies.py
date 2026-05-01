from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import AsyncSessionLocal
from app.core.security import decode_access_token
from app.models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(payload.get("sub", 0))
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User | None:
    """Get user if token provided, None otherwise. Never raises.

    Distinguishes three failure modes:
      * No token / malformed token / no matching user → silent return None.
        These are normal anonymous-traffic paths or bad client input.
      * Database / SQLAlchemy errors during user lookup → log at error level
        and return None. The endpoint still functions for the anonymous code
        path, but operators get visibility into DB outages instead of
        silently demoting authenticated users to guests.
      * Anything else unexpected → log at error level and return None, again
        preserving the never-raise contract while surfacing the failure.
    """
    token = credentials.credentials if credentials else None
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    sub = payload.get("sub")
    if not sub:
        return None

    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        # Malformed `sub` claim — treat as invalid token, no logging needed.
        return None

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user
    except SQLAlchemyError:
        logger.exception(
            "Database error during optional user lookup; treating as anonymous "
            "(user_id=%s)",
            user_id,
        )
    except Exception:
        # Defensive catch-all to honour the "never raises" contract, but log
        # so we notice unexpected exceptions instead of silently swallowing them.
        logger.exception(
            "Unexpected error during optional user lookup; treating as anonymous "
            "(user_id=%s)",
            user_id,
        )
    return None
