from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, JSON, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class HealthJob(Base):
    """Represents a health analysis job that can process multiple assets"""
    __tablename__ = "health_jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True, default="pending")
    payload = Column("payload", JSON, default=dict, nullable=False)
    priority = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    assets = relationship("HealthAsset", back_populates="job", cascade="all, delete-orphan")
    findings = relationship("HealthFinding", back_populates="job", cascade="all, delete-orphan")


class HealthAsset(Base):
    """Represents a health data asset (ECG image, signal file, lab result, etc.) processed in a job"""
    __tablename__ = "health_assets"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("health_jobs.id"), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    hash = Column(String(255), nullable=True, index=True)
    meta = Column("metadata", JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job = relationship("HealthJob", back_populates="assets")
    findings = relationship("HealthFinding", back_populates="asset", cascade="all, delete-orphan")


class HealthFinding(Base):
    """Represents a clinical finding derived from analyzing a health asset"""
    __tablename__ = "health_findings"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("health_jobs.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("health_assets.id"), nullable=True, index=True)
    finding_type = Column(String(50), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(50), nullable=False, index=True)
    icd_code = Column(String(50), nullable=True, index=True)
    confidence = Column(Float, nullable=True)
    meta = Column("metadata", JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job = relationship("HealthJob", back_populates="findings")
    asset = relationship("HealthAsset", back_populates="findings")
