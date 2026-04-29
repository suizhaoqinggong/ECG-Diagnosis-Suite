from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db_models import Base


class HealthJob(Base):
    __tablename__ = "health_jobs"
    __table_args__ = (Index("ix_health_jobs_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    message: Mapped[str] = mapped_column(String(255), nullable=False, default="Queued")
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    assets: Mapped[list["HealthAsset"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    findings: Mapped[list["HealthFinding"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class HealthAsset(Base):
    __tablename__ = "health_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("health_jobs.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped["HealthJob"] = relationship(back_populates="assets")


class HealthFinding(Base):
    __tablename__ = "health_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("health_jobs.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    action_hint: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    job: Mapped["HealthJob"] = relationship(back_populates="findings")
