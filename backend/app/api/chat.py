from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.auth_dependencies import get_current_user
from app.core.database import AsyncSessionLocal
from app.core.rate_limit import check_chat_write_limit
from app.models.chat import ChatMessage, ChatSession
from app.models.enums import MessageRole, MessageStatus, MessageType
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])


def _parse_cursor(cursor: str) -> tuple[datetime, str]:
    parts = cursor.split(",")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cursor",
        )

    try:
        cursor_dt = datetime.fromisoformat(parts[0])
        UUID(parts[1])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cursor",
        )

    return cursor_dt, parts[1]


class SessionCreate(BaseModel):
    id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )
    title: str


class SessionUpdate(BaseModel):
    title: str


class SessionResponse(BaseModel):
    id: str
    title: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    id: str = Field(
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    )
    role: MessageRole
    type: MessageType
    title: str | None = None
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
    title: str | None
    content: str
    attachments: dict | None
    result: dict | None
    status: MessageStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
        return list(result.scalars().all())


@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatSession:
    """Create a new chat session."""
    await check_chat_write_limit(current_user.id, "create-session")

    async with AsyncSessionLocal() as session:
        chat_session = ChatSession(
            id=data.id,
            user_id=current_user.id,
            title=data.title,
        )
        session.add(chat_session)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Session already exists",
            )
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
        for s in result.scalars().all():
            await session.delete(s)
        await session.commit()


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
            cursor_dt, cursor_id = _parse_cursor(cursor)
            query = query.where(
                (ChatMessage.created_at > cursor_dt)
                | ((ChatMessage.created_at == cursor_dt) & (ChatMessage.id > cursor_id))
            )

        query = query.order_by(ChatMessage.created_at, ChatMessage.id).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())


@router.post(
    "/sessions/{session_id}/messages",
    response_model=list[MessageResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_messages(
    session_id: str,
    data: BatchMessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ChatMessage]:
    """Create messages atomically (batch insert with idempotency)."""
    await check_chat_write_limit(current_user.id, "create-messages")

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
        unique_message_ids = set(message_ids)
        if len(unique_message_ids) != len(message_ids):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate message IDs in request",
            )

        result = await session.execute(
            select(ChatMessage.id, ChatMessage.session_id).where(ChatMessage.id.in_(message_ids))
        )
        existing_rows = result.all()
        existing_ids = {row[0] for row in existing_rows}
        foreign_session_ids = {
            row[0] for row in existing_rows if row[1] != session_id
        }

        if foreign_session_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Message IDs already belong to another session",
            )

        if existing_ids:
            if len(existing_ids) == len(message_ids):
                # All exist - return them as success (idempotent)
                result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                    .where(ChatMessage.id.in_(message_ids))
                    .order_by(ChatMessage.created_at, ChatMessage.id)
                )
                return list(result.scalars().all())
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
                title=m.title,
                content=m.content,
                attachments=m.attachments,
                result=m.result,
                result_schema_version=m.result_schema_version,
                status=m.status,
            )
            session.add(msg)
            messages.append(msg)

        # Update session updated_at
        chat_session.updated_at = datetime.now(timezone.utc)

        await session.commit()
        for m in messages:
            await session.refresh(m)

        return messages
