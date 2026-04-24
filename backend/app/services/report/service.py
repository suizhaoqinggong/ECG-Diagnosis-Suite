"""Thin coordinator that composes the template builder and LLM providers.

The public surface (``DiagnosisReportService``, ``get_diagnosis_report_service``)
remains identical to the original monolith so that existing callers and tests
continue to work without changes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from .parser import strip_markdown_fences, parse_llm_text
from .providers import AnthropicCompatibleProvider, OpenAIProvider
from .schemas import DiagnosisEnhancedReport
from .template_builder import TemplateReportBuilder

logger = logging.getLogger(__name__)


class DiagnosisReportService:
    """Generate fallback or LLM-enhanced reports for diagnosis results.

    Delegates template building to ``TemplateReportBuilder`` and LLM calls to
    the configured provider.  Exposes the same method signatures as the
    original monolithic class so that all existing tests keep passing.
    """

    def __init__(self) -> None:
        self._builder = TemplateReportBuilder()
        self._openai_provider = OpenAIProvider()
        self._anthropic_provider = AnthropicCompatibleProvider()

    # ------------------------------------------------------------------
    # Backward-compatible thin wrappers used by existing tests
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        return strip_markdown_fences(text)

    def _parse_llm_text(
        self,
        raw_text: str,
        model_name: str,
        fallback_report: DiagnosisEnhancedReport,
        provider_label: str,
    ) -> Optional[DiagnosisEnhancedReport]:
        return parse_llm_text(raw_text, model_name, fallback_report, provider_label)

    def _build_confidence_phrase(
        self,
        confidence: float,
        prediction: Optional[str] = None,
    ) -> str:
        if prediction is None:
            return self._builder._build_generic_confidence_phrase(confidence)
        return self._builder._build_confidence_phrase(confidence, prediction)

    def _build_follow_up(
        self,
        severity: Optional[str],
        prediction: Optional[str] = None,
    ) -> List[str]:
        if prediction is None:
            return self._builder._build_generic_follow_up(severity)
        return self._builder._build_follow_up(severity, prediction)

    def _build_limitations(self, input_mode: str, confidence: float) -> List[str]:
        return self._builder._build_limitations(input_mode, confidence)

    def build_template_report(
        self,
        *,
        prediction: str,
        confidence: float,
        severity: Optional[str],
        icd_code: Optional[str],
        description: Optional[str],
        recommendations: Optional[List[str]],
        top3_predictions: Optional[List[Dict[str, Any]]],
        input_mode: str,
        metadata: Optional[Dict[str, Any]] = None,
        detected_labels: Optional[List[str]] = None,
        secondary_findings: Optional[List[str]] = None,
    ) -> DiagnosisEnhancedReport:
        return self._builder.build_report(
            prediction=prediction,
            confidence=confidence,
            severity=severity,
            icd_code=icd_code,
            description=description,
            recommendations=recommendations,
            top3_predictions=top3_predictions,
            input_mode=input_mode,
            metadata=metadata,
            detected_labels=detected_labels,
            secondary_findings=secondary_findings,
        )

    async def _generate_with_openai(
        self,
        *,
        prompt_context: Dict[str, Any],
        fallback_report: DiagnosisEnhancedReport,
    ) -> Optional[DiagnosisEnhancedReport]:
        return await self._openai_provider.generate(
            prompt_context=prompt_context,
            fallback_report=fallback_report,
        )

    async def _generate_with_anthropic_compatible(
        self,
        *,
        prompt_context: Dict[str, Any],
        fallback_report: DiagnosisEnhancedReport,
    ) -> Optional[DiagnosisEnhancedReport]:
        return await self._anthropic_provider.generate(
            prompt_context=prompt_context,
            fallback_report=fallback_report,
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def generate_report(
        self,
        *,
        prediction: str,
        confidence: float,
        severity: Optional[str],
        icd_code: Optional[str],
        description: Optional[str],
        recommendations: Optional[List[str]],
        top3_predictions: Optional[List[Dict[str, Any]]],
        all_probabilities: Optional[Dict[str, float]],
        input_mode: str,
        metadata: Optional[Dict[str, Any]] = None,
        detected_labels: Optional[List[str]] = None,
        secondary_findings: Optional[List[str]] = None,
    ) -> DiagnosisEnhancedReport:
        template_kwargs: Dict[str, Any] = {
            "prediction": prediction,
            "confidence": confidence,
            "severity": severity,
            "icd_code": icd_code,
            "description": description,
            "recommendations": recommendations,
            "top3_predictions": top3_predictions,
            "input_mode": input_mode,
            "metadata": metadata,
        }
        if detected_labels is not None:
            template_kwargs["detected_labels"] = detected_labels
        if secondary_findings is not None:
            template_kwargs["secondary_findings"] = secondary_findings

        fallback_report = self.build_template_report(**template_kwargs)

        if not settings.LLM_REPORT_ENABLED:
            return fallback_report

        prompt_context = {
            "prediction": prediction,
            "confidence": confidence,
            "severity": severity,
            "icd_code": icd_code,
            "description": description,
            "recommendations": recommendations,
            "top3_predictions": top3_predictions,
            "all_probabilities": all_probabilities,
            "input_mode": input_mode,
            "metadata": metadata or {},
            "fallback_report": fallback_report.model_dump(mode="json"),
        }

        provider = settings.LLM_REPORT_PROVIDER.lower()

        # Warn early if the chosen provider has no API key configured
        if provider == "openai" and not settings.OPENAI_API_KEY:
            logger.warning(
                "LLM reports are enabled with provider 'openai', but OPENAI_API_KEY is not set. "
                "Falling back to template report."
            )
            return fallback_report
        if provider in {"anthropic", "anthropic_compatible", "zhipu_anthropic"} and not settings.ANTHROPIC_COMPAT_API_KEY:
            logger.warning(
                "LLM reports are enabled with provider '%s', but ANTHROPIC_COMPAT_API_KEY is not set. "
                "Falling back to template report.",
                provider,
            )
            return fallback_report

        try:
            if provider == "openai":
                enhanced_report = await self._generate_with_openai(
                    prompt_context=prompt_context,
                    fallback_report=fallback_report,
                )
            elif provider in {"anthropic", "anthropic_compatible", "zhipu_anthropic"}:
                enhanced_report = await self._generate_with_anthropic_compatible(
                    prompt_context=prompt_context,
                    fallback_report=fallback_report,
                )
            else:
                logger.warning(
                    "Unsupported LLM report provider '%s', falling back to template report.",
                    settings.LLM_REPORT_PROVIDER,
                )
                return fallback_report
        except Exception as exc:
            logger.warning("LLM report generation failed, using fallback report: %s", exc)
            return fallback_report

        return enhanced_report or fallback_report


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_report_service = DiagnosisReportService()


def get_diagnosis_report_service() -> DiagnosisReportService:
    return _report_service
