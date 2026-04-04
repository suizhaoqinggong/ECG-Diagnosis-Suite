"""LLM output parsing utilities.

Handles markdown fence stripping, JSON validation, and field-level fallback
when converting raw LLM text into a ``DiagnosisEnhancedReport``.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .schemas import DiagnosisEnhancedReport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schema for LLM output validation
# ---------------------------------------------------------------------------


class LLMReportBody(BaseModel):
    """Schema enforced on LLM output."""

    model_config = ConfigDict(extra="forbid")

    summary: str
    clinical_interpretation: str
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    follow_up: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


# Backward-compatible alias used by existing tests
_LLMReportBody = LLMReportBody


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def strip_markdown_fences(text: str) -> str:
    """Remove surrounding ```json ... ``` fences that LLMs often add."""
    stripped = text.strip()
    if stripped.startswith("```"):
        # Drop the opening fence line (e.g. ```json or ```)
        stripped = stripped.split("\n", 1)[-1] if "\n" in stripped else stripped[3:]
        # Drop the closing fence
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    return stripped.strip()


def parse_llm_text(
    raw_text: str,
    model_name: str,
    fallback_report: DiagnosisEnhancedReport,
    provider_label: str,
) -> Optional[DiagnosisEnhancedReport]:
    """Parse raw LLM text into a ``DiagnosisEnhancedReport``.

    Handles markdown fences, JSON validation, and field-level fallback.
    Returns ``None`` when the text cannot be parsed.
    """
    cleaned = strip_markdown_fences(raw_text)

    try:
        parsed = _LLMReportBody.model_validate_json(cleaned)
    except Exception as exc:
        logger.warning("%s report returned invalid JSON: %s", provider_label, exc)
        return None

    return DiagnosisEnhancedReport(
        source="llm",
        model=model_name,
        summary=parsed.summary,
        clinical_interpretation=parsed.clinical_interpretation,
        key_findings=parsed.key_findings or fallback_report.key_findings,
        recommendations=parsed.recommendations or fallback_report.recommendations,
        follow_up=parsed.follow_up or fallback_report.follow_up,
        limitations=parsed.limitations or fallback_report.limitations,
    )
