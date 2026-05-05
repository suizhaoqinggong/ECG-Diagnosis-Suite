"""
Database Models
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class DiagnosisRecord(Base):
    """诊断记录表"""
    __tablename__ = "diagnosis_records"
    __table_args__ = (
        Index("ix_diagnosis_records_user", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # 文件信息
    image_path: Mapped[str] = mapped_column(String(255), nullable=False)

    # 用户关联（匿名用户为 null）
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # 诊断结果
    prediction: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    icd_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # 详细信息
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 元数据
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=True)

    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "image_path": self.image_path,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "severity": self.severity,
            "icd_code": self.icd_code,
            "description": self.description,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
