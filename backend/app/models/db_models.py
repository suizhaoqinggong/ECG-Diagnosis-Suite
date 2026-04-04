"""
Database Models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class DiagnosisRecord(Base):
    """诊断记录表"""
    __tablename__ = "diagnosis_records"
    __table_args__ = (
        Index("ix_diagnosis_records_user", "user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # 文件信息
    image_path = Column(String(255), nullable=False)

    # 用户关联（匿名用户为 null）
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # 诊断结果
    prediction = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    severity = Column(String(50))
    icd_code = Column(String(20))

    # 详细信息
    description = Column(Text)
    recommendations = Column(JSON)  # 存储为JSON数组

    # 元数据
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

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
