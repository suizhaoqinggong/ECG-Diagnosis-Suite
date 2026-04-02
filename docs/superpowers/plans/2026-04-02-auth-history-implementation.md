# Auth & Chat History Cloud Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add user registration/login with JWT-based auth and cloud-based conversation history storage to the ECG Diagnosis Suite.

**Architecture:** Backend uses FastAPI with SQLAlchemy async ORM, Alembic migrations, HttpOnly cookie for refresh tokens. Frontend uses a standalone auth store module (not React-dependent) with axios interceptors for token refresh. Dual-mode persistence: anonymous users keep localStorage behavior, logged-in users use cloud storage exclusively.

**Tech Stack:** FastAPI, SQLAlchemy (async), Alembic, python-jose, passlib, slowapi (backend); React, axios, crypto.randomUUID (frontend)

---

## File Structure Overview

### Backend New Files
- `backend/alembic/` - migration directory (initialized by alembic)
- `backend/alembic/versions/001_initial.py` - initial migration with all tables
- `backend/app/models/enums.py` - MessageRole, MessageType, MessageStatus enums
- `backend/app/models/user.py` - User ORM model
- `backend/app/models/chat.py` - ChatSession, ChatMessage ORM models
- `backend/app/models/refresh_token.py` - RefreshToken ORM model
- `backend/app/core/security.py` - password hashing, JWT encoding/decoding
- `backend/app/core/auth_dependencies.py` - get_current_user, get_optional_user
- `backend/app/api/auth.py` - auth router (register, login, refresh, logout, me, change-password, delete-account)
- `backend/app/api/chat.py` - chat router (sessions, messages CRUD)
- `backend/app/services/rate_limiter.py` - rate limiting service

### Backend Modified Files
- `backend/app/models/db_models.py` - add user_id FK to diagnosis_records
- `backend/app/core/config.py` - add SECRET_KEY validation, CORS origins
- `backend/app/core/database.py` - migration-aware init
- `backend/app/main.py` - mount auth/chat routers, CORS config
- `backend/app/api/diagnosis.py` - use get_optional_user, deprecate /history
- `backend/requirements.txt` - add dependencies

### Frontend New Files
- `frontend/src/auth/store.ts` - standalone auth store
- `frontend/src/auth/types.ts` - User, AuthState types
- `frontend/src/auth/api.ts` - auth API functions
- `frontend/src/auth/AuthProvider.tsx` - React context wrapper
- `frontend/src/auth/AuthModal.tsx` - login/register modal
- `frontend/src/auth/UserMenu.tsx` - user dropdown menu
- `frontend/src/api/chat.ts` - chat API functions

### Frontend Modified Files
- `frontend/src/api/client.ts` - add interceptors, withCredentials
- `frontend/src/api/index.ts` - export chatApi
- `frontend/src/types/chat.ts` - update ChatSession (if needed)
- `frontend/src/controllers/useWorkspaceController.ts` - add auth slice, cloud sync logic
- `frontend/src/components/ConversationSidebar.tsx` - hide persistence toggle when logged in, update clear all behavior
- `frontend/src/pages/HomePage.tsx` - add AuthModal, UserMenu trigger
- `frontend/src/App.tsx` - wrap with AuthProvider

---

## Phase 1: Backend Foundation

### Task 1: Add Dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add new dependencies to requirements.txt**

```txt
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
alembic==1.13.1
slowapi==0.1.9
```

- [ ] **Step 2: Install dependencies**

Run: `cd backend && uv pip install -r requirements.txt`

Expected: All packages install without errors

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "deps: add auth and chat history dependencies"
```

### Task 2: Create Enums

**Files:**
- Create: `backend/app/models/enums.py`

- [ ] **Step 1: Create enum definitions**

```python
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageType(str, Enum):
    INTRO = "intro"
    PROMPT = "prompt"
    GUIDANCE = "guidance"
    DIAGNOSIS = "diagnosis"


class MessageStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    ERROR = "error"
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/enums.py
git commit -m "feat: add message enums for chat"
```

### Task 3: Create User Model

**Files:**
- Create: `backend/app/models/user.py`

- [ ] **Step 1: Create User ORM model**

```python
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

if TYPE_CHECKING:
    from backend.app.models.chat import ChatSession
    from backend.app.models.refresh_token import RefreshToken


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/user.py
git commit -m "feat: add User model"
```

### Task 4: Create RefreshToken Model

**Files:**
- Create: `backend/app/models/refresh_token.py`

- [ ] **Step 1: Create RefreshToken ORM model**

```python
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base

if TYPE_CHECKING:
    from backend.app.models.user import User


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        {"mysql_engine": "InnoDB"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    family_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    replaced_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("refresh_tokens.id"),
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/refresh_token.py
git commit -m "feat: add RefreshToken model with rotation support"
```

### Task 5: Create Chat Models

**Files:**
- Create: `backend/app/models/chat.py`

- [ ] **Step 1: Create ChatSession and ChatMessage models**

```python
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.models.enums import MessageRole, MessageStatus, MessageType

if TYPE_CHECKING:
    from backend.app.models.user import User


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_sessions_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New analysis",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_messages_session_created", "session_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[MessageRole] = mapped_column(String(20), nullable=False)
    type: Mapped[MessageType] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result_schema_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[MessageStatus] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/chat.py
git commit -m "feat: add ChatSession and ChatMessage models"
```

### Task 6: Update Existing Diagnosis Records Model

**Files:**
- Modify: `backend/app/models/db_models.py`

- [ ] **Step 1: Add user_id FK to diagnosis_records**

Add imports at top:
```python
from sqlalchemy import ForeignKey, Index
```

Add column to DiagnosisRecord class (before created_at):
```python
user_id: Mapped[int | None] = mapped_column(
    ForeignKey("users.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)
```

Add table args for index:
```python
__table_args__ = (
    Index("ix_diagnosis_records_user", "user_id", "created_at"),
)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/db_models.py
git commit -m "feat: add user_id FK to diagnosis_records"
```

### Task 7: Create Security Utilities

**Files:**
- Create: `backend/app/core/security.py`

- [ ] **Step 1: Create password and JWT utilities**

```python
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: int) -> tuple[str, datetime]:
    """Create JWT access token. Returns (token, expiry)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode: dict[str, Any] = {"sub": str(subject), "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate JWT. Returns payload or None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_refresh_token() -> str:
    """Generate opaque random refresh token."""
    import secrets
    return secrets.token_urlsafe(32)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/security.py
git commit -m "feat: add password hashing and JWT utilities"
```

### Task 8: Create Auth Dependencies

**Files:**
- Create: `backend/app/core/auth_dependencies.py`

- [ ] **Step 1: Create get_current_user and get_optional_user**

```python
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.app.core.security import decode_access_token
from backend.app.models.user import User
from backend.app.core.database import AsyncSessionLocal
from sqlalchemy import select

security = HTTPBearer(auto_error=False)


def get_token(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials:
        return credentials.credentials
    return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    token = get_token(credentials)
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
    """Get user if token provided, None otherwise. Never raises."""
    token = get_token(credentials)
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()
            if user and user.is_active:
                return user
    except Exception:
        pass
    return None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/auth_dependencies.py
git commit -m "feat: add auth dependencies"
```

### Task 9: Update Config for SECRET_KEY Validation

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Add SECRET_KEY validation**

Add to imports:
```python
import sys
```

In the Settings class, after SECRET_KEY definition, add validator:

```python
@field_validator("SECRET_KEY")
@classmethod
def validate_secret_key(cls, v: str) -> str:
    if v == "your-secret-key-change-this":
        print("ERROR: SECRET_KEY is using the default placeholder value.", file=sys.stderr)
        print("Please set a secure SECRET_KEY environment variable.", file=sys.stderr)
        sys.exit(1)
    return v
```

Also ensure CORS_ORIGINS is configurable:

```python
CORS_ORIGINS: list[str] = ["http://localhost:5173"]
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/config.py
git commit -m "feat: validate SECRET_KEY in production"
```

### Task 10: Initialize Alembic

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/` directory

- [ ] **Step 1: Initialize alembic**

Run: `cd backend && alembic init alembic`

- [ ] **Step 2: Configure alembic.ini**

Edit `backend/alembic.ini`:
- Set `sqlalchemy.url = %(DATABASE_URL)s`

- [ ] **Step 3: Update env.py**

Edit `backend/alembic/env.py`:
- Import settings from app.core.config
- Set `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)`
- Import all models for target_metadata

```python
from backend.app.core.config import settings
from backend.app.core.database import Base
from backend.app.models.db_models import DiagnosisRecord
from backend.app.models.user import User
from backend.app.models.chat import ChatSession, ChatMessage
from backend.app.models.refresh_token import RefreshToken

target_metadata = Base.metadata
```

- [ ] **Step 4: Generate initial migration**

Run: `cd backend && alembic revision --autogenerate -m "initial migration with auth and chat"`

- [ ] **Step 5: Commit**

```bash
git add backend/alembic backend/alembic.ini
git commit -m "chore: initialize alembic with initial migration"
```

### Task 11: Update Database Init for Migrations

**Files:**
- Modify: `backend/app/core/database.py`

- [ ] **Step 1: Make init_db migration-aware**

```python
import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

from backend.app.core.config import settings

Base = declarative_base()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def check_migrations_table() -> bool:
    """Check if alembic_version table exists."""
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
        )
        return result.scalar_one_or_none() is not None


async def init_db() -> None:
    """Initialize database.

    In production: require migrations to be run separately.
    In development: create tables if migrations don't exist.
    """
    has_migrations = await check_migrations_table()

    if not has_migrations and settings.DEBUG:
        # Dev mode with fresh DB - create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created (dev mode)")
    elif not has_migrations and not settings.DEBUG:
        raise RuntimeError(
            "Database tables not initialized. Please run: alembic upgrade head"
        )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/core/database.py
git commit -m "feat: migration-aware database init"
```

---

## Phase 2: Backend Auth API

### Task 12: Create Auth Router

**Files:**
- Create: `backend/app/api/auth.py`

This is a large file. I'll split into multiple steps.

- [ ] **Step 1: Create auth router structure and schemas**

```python
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.auth_dependencies import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.security import (
    create_access_token,
    generate_refresh_token,
    get_password_hash,
    verify_password,
)
from backend.app.models.enums import MessageRole, MessageStatus, MessageType
from backend.app.models.refresh_token import RefreshToken
from backend.app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str | None

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    user: UserResponse


def validate_origin(request: Request) -> None:
    """Validate Origin header for CSRF protection."""
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        return  # Allow if no origin (same-origin request)

    allowed_origins = settings.CORS_ORIGINS
    if origin not in allowed_origins:
        # Check if origin starts with any allowed origin
        for allowed in allowed_origins:
            if origin.startswith(allowed):
                return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid origin",
        )
```

- [ ] **Step 2: Add register endpoint**

```python
@router.post("/register", response_model=AuthResponse)
async def register(
    request: Request,
    response: Response,
    data: RegisterRequest,
) -> AuthResponse:
    """Register a new user."""
    validate_origin(request)

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
        token_value = generate_refresh_token()
        import hashlib
        token_hash = hashlib.sha256(token_value.encode()).hexdigest()
        family_id = hashlib.sha256(token_value.encode()).hexdigest()[:16]

        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        session.add(refresh_token)
        await session.commit()

        # Set cookie
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

        # Create access token
        access_token, _ = create_access_token(user.id)

        return AuthResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )
```

- [ ] **Step 3: Add login endpoint**

```python
@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
) -> AuthResponse:
    """Login existing user."""
    validate_origin(request)

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
        token_value = generate_refresh_token()
        import hashlib
        token_hash = hashlib.sha256(token_value.encode()).hexdigest()
        family_id = hashlib.sha256(token_value.encode()).hexdigest()[:16]

        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        session.add(refresh_token)
        await session.commit()

        # Set cookie
        cookie_secure = not settings.DEBUG
        response.set_cookie(
            key="rt",
            value=token_value,
            httponly=True,
            secure=cookie_secure,
            samesite="lax",
            path="/api/auth",
            max_age=7 * 24 * 60 * 60,
        )

        access_token, _ = create_access_token(user.id)

        return AuthResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )
```

- [ ] **Step 4: Add refresh, logout, me endpoints**

```python
@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    rt: Annotated[str | None, Cookie()] = None,
) -> AuthResponse:
    """Refresh access token using refresh token cookie."""
    validate_origin(request)

    if not rt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )

    import hashlib
    token_hash = hashlib.sha256(rt.encode()).hexdigest()

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .options(selectinload(RefreshToken.user))
        )
        token = result.scalar_one_or_none()

        if not token or token.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        # Check for replay attack
        if token.revoked_at:
            # Revoke entire family
            await session.execute(
                RefreshToken.__table__.update()
                .where(RefreshToken.family_id == token.family_id)
                .values(revoked_at=datetime.now(timezone.utc))
            )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token reuse detected",
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
        token.revoked_at = datetime.now(timezone.utc)
        await session.commit()

        # Set new cookie
        cookie_secure = not settings.DEBUG
        response.set_cookie(
            key="rt",
            value=new_token_value,
            httponly=True,
            secure=cookie_secure,
            samesite="lax",
            path="/api/auth",
            max_age=7 * 24 * 60 * 60,
        )

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
    validate_origin(request)

    if rt:
        import hashlib
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
```

- [ ] **Step 5: Add change-password and delete-account endpoints**

```python
@router.post("/change-password")
async def change_password(
    request: Request,
    response: Response,
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Change password - revokes all refresh tokens."""
    validate_origin(request)

    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid old password",
        )

    async with AsyncSessionLocal() as session:
        # Update password
        current_user.hashed_password = get_password_hash(data.new_password)

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
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    """Delete user account and all associated data."""
    validate_origin(request)

    async with AsyncSessionLocal() as session:
        await session.delete(current_user)
        await session.commit()

    response.delete_cookie(key="rt", path="/api/auth")
    return {"message": "Account deleted"}
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/auth.py
git commit -m "feat: add auth router with register, login, refresh, logout"
```

---

## Phase 3: Backend Chat API

### Task 13: Create Chat Router

**Files:**
- Create: `backend/app/api/chat.py`

- [ ] **Step 1: Create chat router schemas and list endpoint**

```python
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.auth_dependencies import get_current_user
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.chat import ChatMessage, ChatSession
from backend.app.models.enums import MessageRole, MessageStatus, MessageType
from backend.app.models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])


class SessionCreate(BaseModel):
    id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    title: str


class SessionUpdate(BaseModel):
    title: str


class SessionResponse(BaseModel):
    id: str
    title: str
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    role: MessageRole
    type: MessageType
    content: str
    attachments: dict | None = None
    result: dict | None = None
    result_schema_version: int | None = None
    status: MessageStatus


class BatchMessageCreate(BaseModel):
    messages: list[MessageCreate]


class MessageResponse(BaseModel):
    id: str
    role: MessageRole
    type: MessageType
    content: str
    attachments: dict | None
    result: dict | None
    status: MessageStatus
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(default=50, ge=1, le=100),
) -> list[ChatSession]:
    """List user's chat sessions."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChatSession)
            .where(ChatSession.user_id == current_user.id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
```

- [ ] **Step 2: Add create and get session endpoints**

```python
@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatSession:
    """Create a new chat session."""
    async with AsyncSessionLocal() as session:
        chat_session = ChatSession(
            id=data.id,
            user_id=current_user.id,
            title=data.title,
        )
        session.add(chat_session)
        await session.commit()
        await session.refresh(chat_session)
        return chat_session


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatSession:
    """Get a single session (metadata only, no messages)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == current_user.id)
        )
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return chat_session
```

- [ ] **Step 3: Add update and delete session endpoints**

```python
@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    data: SessionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatSession:
    """Update session title."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == current_user.id)
        )
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        chat_session.title = data.title
        await session.commit()
        await session.refresh(chat_session)
        return chat_session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a single session."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == current_user.id)
        )
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        await session.delete(chat_session)
        await session.commit()


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete all user's sessions (for 'Clear all history')."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ChatSession).where(ChatSession.user_id == current_user.id)
        )
        sessions = result.scalars().all()
        for s in sessions:
            await session.delete(s)
        await session.commit()
```

- [ ] **Step 4: Add message list endpoint with pagination**

```python
@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    cursor: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[ChatMessage]:
    """List messages for a session with cursor-based pagination."""
    async with AsyncSessionLocal() as session:
        # Verify session ownership
        result = await session.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == current_user.id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        # Parse cursor: "created_at_iso,id"
        query = select(ChatMessage).where(ChatMessage.session_id == session_id)

        if cursor:
            parts = cursor.split(",")
            if len(parts) == 2:
                cursor_dt = datetime.fromisoformat(parts[0])
                cursor_id = parts[1]
                query = query.where(
                    (ChatMessage.created_at > cursor_dt) |
                    ((ChatMessage.created_at == cursor_dt) & (ChatMessage.id > cursor_id))
                )

        query = query.order_by(ChatMessage.created_at, ChatMessage.id).limit(limit)
        result = await session.execute(query)
        return result.scalars().all()
```

- [ ] **Step 5: Add batch message create endpoint**

```python
@router.post("/sessions/{session_id}/messages", response_model=list[MessageResponse], status_code=status.HTTP_201_CREATED)
async def create_messages(
    session_id: str,
    data: BatchMessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ChatMessage]:
    """Create messages atomically (batch insert with idempotency)."""
    async with AsyncSessionLocal() as session:
        # Verify session ownership
        result = await session.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == current_user.id)
        )
        chat_session = result.scalar_one_or_none()
        if not chat_session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        # Check for existing message IDs (idempotency)
        message_ids = [m.id for m in data.messages]
        result = await session.execute(
            select(ChatMessage.id).where(ChatMessage.id.in_(message_ids))
        )
        existing_ids = {row[0] for row in result.all()}

        if existing_ids:
            # All messages must be new, or all must exist (idempotent)
            if len(existing_ids) == len(message_ids):
                # All exist - return them as success
                result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.id.in_(message_ids))
                    .order_by(ChatMessage.created_at, ChatMessage.id)
                )
                return result.scalars().all()
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Partial duplicate message IDs",
                )

        # Create messages
        messages = []
        for m in data.messages:
            msg = ChatMessage(
                id=m.id,
                session_id=session_id,
                role=m.role,
                type=m.type,
                content=m.content,
                attachments=m.attachments,
                result=m.result,
                result_schema_version=m.result_schema_version,
                status=m.status,
            )
            session.add(msg)
            messages.append(msg)

        # Update session updated_at
        from datetime import timezone
        chat_session.updated_at = datetime.now(timezone.utc)

        await session.commit()
        for m in messages:
            await session.refresh(m)

        return messages
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/chat.py
git commit -m "feat: add chat router for sessions and messages"
```

---

## Phase 4: Backend Integration

### Task 14: Update Main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Import and mount routers, update CORS**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import auth, chat, diagnosis
from backend.app.core.config import settings
from backend.app.core.database import init_db

app = FastAPI(title="ECG Diagnosis API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,  # Important for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(diagnosis.router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    await init_db()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: mount auth and chat routers, enable credentials in CORS"
```

### Task 15: Update Diagnosis API

**Files:**
- Modify: `backend/app/api/diagnosis.py`

- [ ] **Step 1: Add optional auth to diagnosis endpoints**

Add import:
```python
from backend.app.core.auth_dependencies import get_optional_user
from backend.app.models.user import User
```

Update diagnose endpoint signature:
```python
async def diagnose(
    request: Request,
    file: UploadFile = File(...),
    current_user: Annotated[User | None, Depends(get_optional_user)] = None,
) -> DiagnosisResponse:
```

When saving diagnosis record, set user_id:
```python
record = DiagnosisRecord(
    # ... existing fields ...
    user_id=current_user.id if current_user else None,
)
```

Do the same for diagnose_dat endpoint.

- [ ] **Step 2: Deprecate /api/history**

Add deprecation note or remove the endpoint. For now, keep but add deprecated flag:

```python
@router.get("/history", deprecated=True)
async def get_history(...) -> list[DiagnosisRecord]:
    """Deprecated: Use chat API for conversation history."""
    ...
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/diagnosis.py
git commit -m "feat: add optional auth to diagnosis, deprecate /history"
```

---

## Phase 5: Frontend Auth Foundation

### Task 16: Create Auth Types

**Files:**
- Create: `frontend/src/auth/types.ts`

- [ ] **Step 1: Create auth type definitions**

```typescript
export interface User {
  id: number
  email: string
  display_name: string | null
}

export interface AuthState {
  user: User | null
  accessToken: string | null
  isLoading: boolean
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  display_name?: string
}

export interface AuthResponse {
  access_token: string
  user: User
}

export type AuthListener = (state: AuthState) => void
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/auth/types.ts
git commit -m "feat: add auth types"
```

### Task 17: Create Auth Store

**Files:**
- Create: `frontend/src/auth/store.ts`

- [ ] **Step 1: Create standalone auth store**

```typescript
import type { AuthState, AuthListener, User } from './types'

const initialState: AuthState = {
  user: null,
  accessToken: null,
  isLoading: true,
}

let state: AuthState = { ...initialState }
const listeners: Set<AuthListener> = new Set()

function setState(partial: Partial<AuthState>) {
  state = { ...state, ...partial }
  listeners.forEach((listener) => listener(state))
}

export function getState(): AuthState {
  return state
}

export function subscribe(listener: AuthListener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function getToken(): string | null {
  return state.accessToken
}

export function setAuth(user: User, accessToken: string) {
  setState({ user, accessToken, isLoading: false })
}

export function clearAuth() {
  setState({ user: null, accessToken: null, isLoading: false })
}

export function setLoading(loading: boolean) {
  setState({ isLoading: loading })
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/auth/store.ts
git commit -m "feat: add standalone auth store"
```

### Task 18: Create Auth API

**Files:**
- Create: `frontend/src/auth/api.ts`

- [ ] **Step 1: Create auth API functions**

```typescript
import apiClient from '@/api/client'
import type { AuthResponse, LoginRequest, RegisterRequest } from './types'

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/api/auth/login', data, {
    withCredentials: true,
  })
  return response.data
}

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/api/auth/register', data, {
    withCredentials: true,
  })
  return response.data
}

export async function refresh(): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>(
    '/api/auth/refresh',
    {},
    { withCredentials: true }
  )
  return response.data
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/auth/logout', {}, { withCredentials: true })
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await apiClient.post('/api/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
}

export async function deleteAccount(): Promise<void> {
  await apiClient.post('/api/auth/delete-account', {}, { withCredentials: true })
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/auth/api.ts
git commit -m "feat: add auth API functions"
```

### Task 19: Create AuthProvider

**Files:**
- Create: `frontend/src/auth/AuthProvider.tsx`

- [ ] **Step 1: Create React context wrapper**

```typescript
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { AuthState, User } from './types'
import { getState, subscribe, setAuth, clearAuth, setLoading } from './store'
import { refresh } from './api'

interface AuthContextValue extends AuthState {
  setAuthenticated: (user: User, accessToken: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setLocalState] = useState<AuthState>(getState())

  useEffect(() => {
    return subscribe((newState) => setLocalState(newState))
  }, [])

  useEffect(() => {
    // Try to refresh on mount
    refresh()
      .then((response) => {
        setAuth(response.user, response.access_token)
      })
      .catch(() => {
        clearAuth()
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  const setAuthenticated = (user: User, accessToken: string) => {
    setAuth(user, accessToken)
  }

  const logout = () => {
    clearAuth()
  }

  const value: AuthContextValue = {
    ...state,
    setAuthenticated,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/auth/AuthProvider.tsx
git commit -m "feat: add AuthProvider React context"
```

### Task 20: Update API Client with Interceptors

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add request and response interceptors**

```typescript
import axios from 'axios'
import { getToken } from '@/auth/store'
import { refresh } from '@/auth/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || ''

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
})

// Request interceptor: add auth header
apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // Add withCredentials for auth endpoints
  if (config.url?.startsWith('/api/auth')) {
    config.withCredentials = true
  }
  return config
})

// Response interceptor: handle 401 and refresh
let isRefreshing = false
let refreshPromise: Promise<void> | null = null

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (!originalRequest || !error.response || error.response.status !== 401) {
      return Promise.reject(error)
    }

    // Don't retry auth endpoint requests
    if (originalRequest.url?.startsWith('/api/auth')) {
      return Promise.reject(error)
    }

    // Mark retried requests
    if (originalRequest._retry) {
      return Promise.reject(error)
    }
    originalRequest._retry = true

    // Single-flight refresh
    if (!isRefreshing) {
      isRefreshing = true
      refreshPromise = refresh()
        .then((response) => {
          const { setAuth } = await import('@/auth/store')
          setAuth(response.user, response.access_token)
        })
        .catch(() => {
          const { clearAuth } = await import('@/auth/store')
          clearAuth()
        })
        .finally(() => {
          isRefreshing = false
          refreshPromise = null
        })
    }

    // Wait for refresh
    if (refreshPromise) {
      try {
        await refreshPromise
        // Retry original request
        return apiClient(originalRequest)
      } catch {
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  }
)

function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error) && error.response?.data) {
    const data = error.response.data as { detail?: string; message?: string }
    return data.detail ?? data.message ?? error.message
  }
  if (error instanceof Error) return error.message
  return 'Analysis failed'
}

export { extractErrorMessage }
export default apiClient
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: add auth interceptors to api client"
```

---

## Phase 6: Frontend Chat API

### Task 21: Create Chat API

**Files:**
- Create: `frontend/src/api/chat.ts`

- [ ] **Step 1: Create chat API functions**

```typescript
import apiClient from './client'
import type { MessageRole, MessageStatus, MessageType } from '@/types/chat'

export interface SessionResponse {
  id: string
  title: string
  updated_at: string
}

export interface MessageResponse {
  id: string
  role: MessageRole
  type: MessageType
  content: string
  attachments: Record<string, unknown> | null
  result: Record<string, unknown> | null
  status: MessageStatus
  created_at: string
}

export interface MessageCreate {
  id: string
  role: MessageRole
  type: MessageType
  content: string
  attachments?: Record<string, unknown> | null
  result?: Record<string, unknown> | null
  result_schema_version?: number | null
  status: MessageStatus
}

export const chatApi = {
  async listSessions(limit = 50): Promise<SessionResponse[]> {
    const response = await apiClient.get<SessionResponse[]>(
      `/api/chat/sessions?limit=${limit}`
    )
    return response.data
  },

  async createSession(id: string, title: string): Promise<SessionResponse> {
    const response = await apiClient.post<SessionResponse>('/api/chat/sessions', {
      id,
      title,
    })
    return response.data
  },

  async getSession(sessionId: string): Promise<SessionResponse> {
    const response = await apiClient.get<SessionResponse>(
      `/api/chat/sessions/${sessionId}`
    )
    return response.data
  },

  async updateSession(sessionId: string, title: string): Promise<SessionResponse> {
    const response = await apiClient.patch<SessionResponse>(
      `/api/chat/sessions/${sessionId}`,
      { title }
    )
    return response.data
  },

  async deleteSession(sessionId: string): Promise<void> {
    await apiClient.delete(`/api/chat/sessions/${sessionId}`)
  },

  async deleteAllSessions(): Promise<void> {
    await apiClient.delete('/api/chat/sessions')
  },

  async listMessages(
    sessionId: string,
    cursor?: string,
    limit = 50
  ): Promise<MessageResponse[]> {
    const params = new URLSearchParams()
    params.set('limit', String(limit))
    if (cursor) params.set('cursor', cursor)

    const response = await apiClient.get<MessageResponse[]>(
      `/api/chat/sessions/${sessionId}/messages?${params.toString()}`
    )
    return response.data
  },

  async createMessages(
    sessionId: string,
    messages: MessageCreate[]
  ): Promise<MessageResponse[]> {
    const response = await apiClient.post<MessageResponse[]>(
      `/api/chat/sessions/${sessionId}/messages`,
      { messages }
    )
    return response.data
  },
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/chat.ts
git commit -m "feat: add chat API functions"
```

### Task 22: Export Chat API

**Files:**
- Modify: `frontend/src/api/index.ts`

- [ ] **Step 1: Export chatApi**

Add to existing exports:
```typescript
export { chatApi } from './chat'
export type { SessionResponse, MessageResponse, MessageCreate } from './chat'
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/index.ts
git commit -m "feat: export chatApi"
```

---

## Phase 7: Frontend Components

### Task 23: Create AuthModal Component

**Files:**
- Create: `frontend/src/auth/AuthModal.tsx`

- [ ] **Step 1: Create auth modal component**

```typescript
import { useState } from 'react'
import { login, register } from './api'
import { useAuth } from './AuthProvider'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  defaultTab?: 'login' | 'register'
}

export function AuthModal({ isOpen, onClose, defaultTab = 'login' }: AuthModalProps) {
  const [tab, setTab] = useState(defaultTab)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setAuthenticated } = useAuth()

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (tab === 'register') {
        if (password !== confirmPassword) {
          setError('Passwords do not match')
          setLoading(false)
          return
        }
        if (password.length < 8) {
          setError('Password must be at least 8 characters')
          setLoading(false)
          return
        }
        const response = await register({
          email,
          password,
          display_name: displayName || undefined,
        })
        setAuthenticated(response.user, response.access_token)
      } else {
        const response = await login({ email, password })
        setAuthenticated(response.user, response.access_token)
      }
      onClose()
    } catch (err) {
      setError(tab === 'login' ? 'Invalid credentials' : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setTab('login')}
            className={`pb-2 ${tab === 'login' ? 'border-b-2 border-blue-500 font-medium' : ''}`}
          >
            Login
          </button>
          <button
            onClick={() => setTab('register')}
            className={`pb-2 ${tab === 'register' ? 'border-b-2 border-blue-500 font-medium' : ''}`}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {tab === 'register' && (
            <div>
              <label className="block text-sm font-medium mb-1">Display Name (optional)</label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full border rounded px-3 py-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="w-full border rounded px-3 py-2"
            />
          </div>

          {tab === 'register' && (
            <div>
              <label className="block text-sm font-medium mb-1">Confirm Password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="w-full border rounded px-3 py-2"
              />
            </div>
          )}

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border rounded"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
            >
              {loading ? 'Loading...' : tab === 'login' ? 'Login' : 'Register'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/auth/AuthModal.tsx
git commit -m "feat: add AuthModal component"
```

### Task 24: Create UserMenu Component

**Files:**
- Create: `frontend/src/auth/UserMenu.tsx`

- [ ] **Step 1: Create user menu component**

```typescript
import { useState } from 'react'
import { logout, changePassword, deleteAccount } from './api'
import { useAuth } from './AuthProvider'

export function UserMenu() {
  const { user, logout: logoutState } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const [showChangePassword, setShowChangePassword] = useState(false)
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  if (!user) return null

  const handleLogout = async () => {
    try {
      await logout()
    } finally {
      logoutState()
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      await changePassword(oldPassword, newPassword)
      setSuccess('Password changed. You will need to log in again on other devices.')
      setOldPassword('')
      setNewPassword('')
    } catch {
      setError('Failed to change password')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (!confirm('Are you sure? This will permanently delete your account and all data.')) {
      return
    }
    try {
      await deleteAccount()
      logoutState()
    } catch {
      alert('Failed to delete account')
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded hover:bg-gray-100"
      >
        <span className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center">
          {(user.display_name || user.email).charAt(0).toUpperCase()}
        </span>
        <span className="hidden sm:inline">{user.display_name || user.email}</span>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-full mt-1 bg-white border rounded-lg shadow-lg z-50 min-w-[200px]">
            <div className="p-3 border-b">
              <p className="font-medium">{user.display_name || user.email}</p>
              <p className="text-sm text-gray-500">{user.email}</p>
            </div>
            <button
              onClick={() => {
                setIsOpen(false)
                setShowChangePassword(true)
              }}
              className="w-full text-left px-4 py-2 hover:bg-gray-100"
            >
              Change Password
            </button>
            <button
              onClick={() => {
                setIsOpen(false)
                handleDeleteAccount()
              }}
              className="w-full text-left px-4 py-2 text-red-600 hover:bg-gray-100"
            >
              Delete Account
            </button>
            <div className="border-t">
              <button
                onClick={handleLogout}
                className="w-full text-left px-4 py-2 hover:bg-gray-100"
              >
                Logout
              </button>
            </div>
          </div>
        </>
      )}

      {showChangePassword && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <form
            onSubmit={handleChangePassword}
            className="bg-white rounded-lg p-6 w-full max-w-sm"
          >
            <h3 className="text-lg font-medium mb-4">Change Password</h3>
            <div className="space-y-3">
              <input
                type="password"
                placeholder="Current password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
                className="w-full border rounded px-3 py-2"
              />
              <input
                type="password"
                placeholder="New password (min 8 chars)"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                className="w-full border rounded px-3 py-2"
              />
            </div>
            {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
            {success && <p className="text-green-500 text-sm mt-2">{success}</p>}
            <div className="flex gap-3 mt-4">
              <button
                type="button"
                onClick={() => setShowChangePassword(false)}
                className="flex-1 px-4 py-2 border rounded"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-2 bg-blue-500 text-white rounded disabled:opacity-50"
              >
                Change
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/auth/UserMenu.tsx
git commit -m "feat: add UserMenu component"
```

---

## Phase 8: Frontend Integration

### Task 25: Update App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Wrap with AuthProvider**

```typescript
import { Toaster } from 'react-hot-toast'
import ErrorBoundary from './components/ErrorBoundary'
import HomePage from './pages/HomePage'
import { AuthProvider } from './auth/AuthProvider'

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <div className="min-h-screen bg-transparent text-[var(--ink)]">
          <HomePage />
        </div>
        <Toaster
          position="top-center"
          toastOptions={{
            duration: 3200,
            style: {
              borderRadius: '18px',
              background: 'rgba(255, 252, 247, 0.96)',
              color: '#2e2a26',
              boxShadow: '0 18px 40px rgba(84, 69, 53, 0.12)',
            },
          }}
        />
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: wrap app with AuthProvider"
```

### Task 26: Update Session ID Generation

**Files:**
- Modify: `frontend/src/controllers/useWorkspaceController.ts`

- [ ] **Step 1: Replace session ID generation with crypto.randomUUID**

Find the CREATE_SESSION action and update the ID generation:

```typescript
// Before:
// id: `${Date.now()}-${Math.random().toString(36).slice(2)}`

// After:
id: crypto.randomUUID()
```

Also update any other places that generate IDs for messages:

```typescript
// For messages:
id: crypto.randomUUID()
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/controllers/useWorkspaceController.ts
git commit -m "feat: use crypto.randomUUID for session and message IDs"
```

### Task 27: Update Workspace Controller for Auth

**Files:**
- Modify: `frontend/src/controllers/useWorkspaceController.ts`

This is a large task. Add auth slice and cloud sync logic.

- [ ] **Step 1: Add auth to WorkspaceState**

Add to WorkspaceState interface:
```typescript
export interface WorkspaceState {
  persisted: {
    sessions: ChatSession[]
    activeSessionId: string
    persistenceEnabled: boolean
    storageVersion: number
  }
  auth: {
    isAuthenticated: boolean
    hasCheckedAuth: boolean
  }
  composer: { ... }
  // ... rest unchanged
}
```

- [ ] **Step 2: Add auth actions to reducer**

Add action types:
```typescript
| { type: 'SET_AUTH_STATUS'; isAuthenticated: boolean }
| { type: 'SET_AUTH_CHECKED' }
```

Add reducer cases:
```typescript
case 'SET_AUTH_STATUS':
  return { ...state, auth: { ...state.auth, isAuthenticated: action.isAuthenticated } }
case 'SET_AUTH_CHECKED':
  return { ...state, auth: { ...state.auth, hasCheckedAuth: true } }
```

- [ ] **Step 3: Add cloud sync functions**

Add async thunks (or use useEffect pattern) for:
- syncSessionToCloud(sessionId)
- loadSessionsFromCloud()
- deleteSessionFromCloud(sessionId)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/controllers/useWorkspaceController.ts
git commit -m "feat: add auth state and cloud sync to workspace controller"
```

### Task 28: Update ConversationSidebar

**Files:**
- Modify: `frontend/src/components/ConversationSidebar.tsx`

- [ ] **Step 1: Hide persistence toggle when authenticated**

Update props to include isAuthenticated, then conditionally render the toggle:

```typescript
{!isAuthenticated && (
  <label className="flex items-center gap-2 text-sm">
    <input
      type="checkbox"
      checked={persistenceEnabled}
      onChange={onTogglePersistence}
    />
    Save history on this device
  </label>
)}
```

- [ ] **Step 2: Update clear all confirmation**

Change confirmation message based on auth status:

```typescript
const handleClearAll = () => {
  const message = isAuthenticated
    ? 'This will delete all conversations from the server. This cannot be undone.'
    : 'This will clear all local conversation history. This cannot be undone.'

  if (confirm(message)) {
    onClearAllSessions()
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ConversationSidebar.tsx
git commit -m "feat: update sidebar for auth state"
```

### Task 29: Update HomePage

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`

- [ ] **Step 1: Add auth UI elements**

Import and use:
```typescript
import { useAuth } from '@/auth/AuthProvider'
import { AuthModal } from '@/auth/AuthModal'
import { UserMenu } from '@/auth/UserMenu'
```

Add state for modal:
```typescript
const [showAuthModal, setShowAuthModal] = useState(false)
```

Add user menu to header area, auth icon button to trigger modal.

- [ ] **Step 2: Add AuthModal to render**

```typescript
<AuthModal
  isOpen={showAuthModal}
  onClose={() => setShowAuthModal(false)}
/>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/HomePage.tsx
git commit -m "feat: add auth UI to home page"
```

---

## Phase 9: Testing

### Task 30: Create Backend Auth Tests

**Files:**
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write auth endpoint tests**

```python
import pytest
from fastapi.testclient import TestClient


def test_register_success(client: TestClient):
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "display_name": "Test User"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test@example.com"


def test_register_duplicate_email(client: TestClient):
    # Register once
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    # Try again
    response = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 400


def test_login_success(client: TestClient):
    # Register first
    client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    # Login
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_invalid_credentials(client: TestClient):
    response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/test_auth.py
git commit -m "test: add auth endpoint tests"
```

### Task 31: Create Backend Chat Tests

**Files:**
- Create: `backend/tests/test_chat.py`

- [ ] **Step 1: Write chat endpoint tests**

```python
import pytest
from fastapi.testclient import TestClient


def test_create_session_unauthorized(client: TestClient):
    response = client.post("/api/chat/sessions", json={
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Test Session"
    })
    assert response.status_code == 401


def test_create_session_authorized(client: TestClient, auth_headers: dict):
    response = client.post("/api/chat/sessions", json={
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Test Session"
    }, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["title"] == "Test Session"


def test_create_messages_authorized(client: TestClient, auth_headers: dict):
    # Create session first
    session_id = "550e8400-e29b-41d4-a716-446655440000"
    client.post("/api/chat/sessions", json={
        "id": session_id,
        "title": "Test"
    }, headers=auth_headers)

    # Add messages
    response = client.post(f"/api/chat/sessions/{session_id}/messages", json={
        "messages": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440001",
                "role": "user",
                "type": "prompt",
                "content": "Test message",
                "status": "completed"
            }
        ]
    }, headers=auth_headers)
    assert response.status_code == 201
    assert len(response.json()) == 1
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/test_chat.py
git commit -m "test: add chat endpoint tests"
```

---

## Phase 10: Documentation

### Task 32: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add auth and chat documentation**

Add sections for:
- Authentication flow
- Database migrations (alembic commands)
- Environment variables (SECRET_KEY requirement)
- New API endpoints

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with auth and chat info"
```

---

## Summary Checklist

### Backend
- [ ] Dependencies added (python-jose, passlib, alembic, slowapi)
- [ ] Enums created (MessageRole, MessageType, MessageStatus)
- [ ] Models created (User, RefreshToken, ChatSession, ChatMessage)
- [ ] Existing model updated (diagnosis_records.user_id)
- [ ] Security utilities (password hashing, JWT)
- [ ] Auth dependencies (get_current_user, get_optional_user)
- [ ] Config validation (SECRET_KEY check)
- [ ] Alembic initialized with initial migration
- [ ] Auth router (register, login, refresh, logout, me, change-password, delete-account)
- [ ] Chat router (sessions CRUD, messages with pagination)
- [ ] Main.py updated (routers mounted, CORS with credentials)
- [ ] Diagnosis API updated (optional auth, deprecate history)

### Frontend
- [ ] Auth types created
- [ ] Auth store created (standalone)
- [ ] Auth API created
- [ ] AuthProvider created
- [ ] API client updated (interceptors, withCredentials)
- [ ] Chat API created
- [ ] AuthModal component created
- [ ] UserMenu component created
- [ ] App.tsx wrapped with AuthProvider
- [ ] Session IDs use crypto.randomUUID
- [ ] Workspace controller updated (auth state, cloud sync)
- [ ] ConversationSidebar updated (toggle visibility, clear confirmation)
- [ ] HomePage updated (auth UI)

### Testing
- [ ] Backend auth tests
- [ ] Backend chat tests

### Documentation
- [ ] CLAUDE.md updated

---

## Post-Implementation

After all tasks are complete:

1. Run full test suite: `pytest backend/tests/`
2. Run frontend type check: `cd frontend && npm run lint`
3. Run frontend tests: `cd frontend && npm test`
4. Manual testing checklist:
   - [ ] Register new account
   - [ ] Login with existing account
   - [ ] Create session while logged in
   - [ ] Add messages to session
   - [ ] Refresh page - session persists
   - [ ] Logout and login again - sessions still there
   - [ ] Anonymous mode still works
   - [ ] Login migration prompt appears
   - [ ] Change password works
   - [ ] Delete account works
