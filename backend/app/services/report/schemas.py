"""Pydantic schemas shared across report sub-modules."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class DiagnosisEnhancedReport(BaseModel):
    """Structured narrative report returned to API clients."""

    source: Literal["template", "llm"]
    model: Optional[str] = None
    summary: str
    clinical_interpretation: str
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    follow_up: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
