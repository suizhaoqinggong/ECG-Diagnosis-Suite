"""
Sliding-window rate limiter.

Uses in-memory storage in development/test by default, and a
database-backed shared window in production.
"""

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock
import time

from fastapi import HTTPException, Request, status
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.rate_limit import RateLimitCounter


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def check(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
        detail: str,
    ) -> None:
        if settings.effective_rate_limit_backend == "database":
            await self._check_database(
                key=key,
                limit=limit,
                window_seconds=window_seconds,
                detail=detail,
            )
            return

        self._check_memory(
            key=key,
            limit=limit,
            window_seconds=window_seconds,
            detail=detail,
        )

    def _check_memory(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
        detail: str,
    ) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=detail,
                )

            events.append(now)

    def reset(self) -> None:
        self._reset_memory()
        if settings.effective_rate_limit_backend == "database":
            try:
                asyncio.run(self._reset_database())
            except RuntimeError:
                # reset() is only used in synchronous test fixtures; if a loop is
                # already running, defer database cleanup to the caller.
                pass

    def _reset_memory(self) -> None:
        with self._lock:
            self._events.clear()

    async def _reset_database(self) -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(RateLimitCounter))
            await session.commit()

    async def _check_database(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
        detail: str,
    ) -> None:
        now = datetime.now(timezone.utc)
        now_ts = int(now.timestamp())
        window_start = now_ts - (now_ts % window_seconds)
        expires_at = datetime.fromtimestamp(
            window_start + window_seconds,
            tz=timezone.utc,
        )

        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(RateLimitCounter).where(RateLimitCounter.expires_at <= now)
            )

            if await self._try_increment_database_window(
                session=session,
                key=key,
                window_start=window_start,
                limit=limit,
            ):
                await session.commit()
                return

            result = await session.execute(
                select(RateLimitCounter.hits)
                .where(RateLimitCounter.scope_key == key)
                .where(RateLimitCounter.window_start == window_start)
            )
            current_hits = result.scalar_one_or_none()

            if current_hits is None:
                session.add(
                    RateLimitCounter(
                        scope_key=key,
                        window_start=window_start,
                        hits=1,
                        expires_at=expires_at,
                    )
                )
                try:
                    await session.commit()
                    return
                except IntegrityError:
                    await session.rollback()
                    async with AsyncSessionLocal() as retry_session:
                        if await self._try_increment_database_window(
                            session=retry_session,
                            key=key,
                            window_start=window_start,
                            limit=limit,
                        ):
                            await retry_session.commit()
                            return
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=detail,
                    )

            if current_hits >= limit:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=detail,
                )

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
            )

    async def _try_increment_database_window(
        self,
        *,
        session,
        key: str,
        window_start: int,
        limit: int,
    ) -> bool:
        result = await session.execute(
            update(RateLimitCounter)
            .where(RateLimitCounter.scope_key == key)
            .where(RateLimitCounter.window_start == window_start)
            .where(RateLimitCounter.hits < limit)
            .values(hits=RateLimitCounter.hits + 1)
        )
        return result.rowcount == 1


rate_limiter = SlidingWindowRateLimiter()


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def check_register_limit(request: Request, email: str) -> None:
    await rate_limiter.check(
        key=f"auth:register:ip:{_client_ip(request)}",
        limit=10,
        window_seconds=60,
        detail="Too many registration attempts. Please try again later.",
    )
    await rate_limiter.check(
        key=f"auth:register:email:{email.lower()}",
        limit=5,
        window_seconds=60,
        detail="Too many registration attempts for this email. Please try again later.",
    )


async def check_login_limit(request: Request, email: str) -> None:
    await rate_limiter.check(
        key=f"auth:login:ip:{_client_ip(request)}",
        limit=10,
        window_seconds=60,
        detail="Too many login attempts. Please try again later.",
    )
    await rate_limiter.check(
        key=f"auth:login:email:{email.lower()}",
        limit=5,
        window_seconds=60,
        detail="Too many login attempts for this email. Please try again later.",
    )


async def check_refresh_ip_limit(request: Request) -> None:
    await rate_limiter.check(
        key=f"auth:refresh:ip:{_client_ip(request)}",
        limit=10,
        window_seconds=60,
        detail="Too many refresh attempts. Please try again later.",
    )


async def check_refresh_user_limit(user_id: int) -> None:
    await rate_limiter.check(
        key=f"auth:refresh:user:{user_id}",
        limit=20,
        window_seconds=60,
        detail="Too many refresh attempts for this account. Please try again later.",
    )


async def check_chat_write_limit(user_id: int, action: str) -> None:
    await rate_limiter.check(
        key=f"chat:write:{action}:user:{user_id}",
        limit=30,
        window_seconds=60,
        detail="Too many chat write requests. Please try again later.",
    )


async def check_diagnosis_anonymous_limit(request: Request) -> None:
    """Rate limit for anonymous (unauthenticated) diagnosis requests."""
    await rate_limiter.check(
        key=f"diagnosis:anonymous:ip:{_client_ip(request)}",
        limit=5,
        window_seconds=60,
        detail="Too many diagnosis requests. Please sign in or try again later.",
    )


async def check_diagnosis_authenticated_limit(user_id: int) -> None:
    """Rate limit for authenticated diagnosis requests (higher quota)."""
    await rate_limiter.check(
        key=f"diagnosis:authenticated:user:{user_id}",
        limit=30,
        window_seconds=60,
        detail="Too many diagnosis requests. Please try again later.",
    )
