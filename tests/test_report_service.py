"""
Protective tests for diagnosis_report_service.

These characterization tests lock in the current behavior of the report
service so that the P1-5 refactoring (split into template builder,
LLM providers, and parser) can proceed safely.
"""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.diagnosis_report_service import (
    DiagnosisEnhancedReport,
    DiagnosisReportService,
    _LLMReportBody,
    get_diagnosis_report_service,
)
from app.core.config import settings


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc() -> DiagnosisReportService:
    return DiagnosisReportService()


def _template_kwargs(**overrides):
    """Keyword args accepted by build_template_report."""
    base = dict(
        prediction="心肌梗死",
        confidence=0.82,
        severity="严重",
        icd_code="I21.0",
        description="心电图提示可能存在心肌梗死。",
        recommendations=[
            "立即就医急诊科",
            "需要紧急冠脉造影评估",
        ],
        top3_predictions=[
            {"class": "心肌梗死", "probability": 0.82},
            {"class": "ST-T改变", "probability": 0.10},
            {"class": "正常", "probability": 0.05},
        ],
        input_mode="image",
        metadata=None,
    )
    base.update(overrides)
    return base


def _generate_kwargs(**overrides):
    """Keyword args accepted by generate_report (includes all_probabilities)."""
    base = _template_kwargs()
    base["all_probabilities"] = {
        "心肌梗死": 0.82, "ST-T改变": 0.10, "正常": 0.05,
        "传导障碍": 0.02, "心室肥大": 0.01,
    }
    base.update(overrides)
    return base


# ===========================================================================
# Template report builder
# ===========================================================================


class TestBuildTemplateReport:
    """Tests for DiagnosisReportService.build_template_report()."""

    def test_returns_template_source(self, svc):
        report = svc.build_template_report(**_template_kwargs())
        assert report.source == "template"
        assert report.model is None

    def test_summary_contains_prediction_and_confidence(self, svc):
        report = svc.build_template_report(**_template_kwargs())
        assert "心肌梗死" in report.summary
        assert "82.0%" in report.summary

    def test_clinical_interpretation_includes_description(self, svc):
        report = svc.build_template_report(**_template_kwargs())
        assert "心肌梗死" in report.clinical_interpretation
        assert "I21.0" in report.clinical_interpretation

    def test_clinical_interpretation_includes_severity(self, svc):
        report = svc.build_template_report(**_template_kwargs())
        assert "严重" in report.clinical_interpretation

    def test_clinical_interpretation_without_icd_code(self, svc):
        report = svc.build_template_report(**_template_kwargs(icd_code=None))
        assert "ICD" not in report.clinical_interpretation

    def test_clinical_interpretation_includes_sample_rate_from_metadata(self, svc):
        report = svc.build_template_report(**_template_kwargs(metadata={"fs": 500}))
        assert "500 Hz" in report.clinical_interpretation

    def test_key_findings_include_prediction_and_severity(self, svc):
        report = svc.build_template_report(**_template_kwargs())
        assert any("心肌梗死" in f for f in report.key_findings)
        assert any("严重" in f for f in report.key_findings)

    def test_key_findings_include_icd_code(self, svc):
        report = svc.build_template_report(**_template_kwargs())
        assert any("I21.0" in f for f in report.key_findings)

    def test_key_findings_include_alternatives_from_top3(self, svc):
        report = svc.build_template_report(**_template_kwargs())
        alternatives_text = [f for f in report.key_findings if "高置信类别" in f]
        assert len(alternatives_text) == 1
        assert "ST-T改变" in alternatives_text[0]

    def test_key_findings_without_top3(self, svc):
        report = svc.build_template_report(**_template_kwargs(top3_predictions=None))
        assert not any("高置信类别" in f for f in report.key_findings)

    def test_recommendations_passthrough(self, svc):
        recs = ["Rec A", "Rec B"]
        report = svc.build_template_report(**_template_kwargs(recommendations=recs))
        assert report.recommendations == recs

    def test_recommendations_default_when_none(self, svc):
        report = svc.build_template_report(**_template_kwargs(recommendations=None))
        assert len(report.recommendations) >= 2
        assert any("综合判断" in r for r in report.recommendations)

    def test_recommendations_default_when_empty(self, svc):
        report = svc.build_template_report(**_template_kwargs(recommendations=[]))
        assert len(report.recommendations) >= 2

    def test_follow_up_severe(self, svc):
        report = svc.build_template_report(**_template_kwargs(severity="严重"))
        assert any("急诊" in f for f in report.follow_up)

    def test_follow_up_moderate(self, svc):
        report = svc.build_template_report(**_template_kwargs(severity="中等"))
        assert any("随访" in f for f in report.follow_up)

    def test_follow_up_normal(self, svc):
        report = svc.build_template_report(**_template_kwargs(severity="正常"))
        assert any("常规" in f or "门诊" in f for f in report.follow_up)

    def test_follow_up_none(self, svc):
        report = svc.build_template_report(**_template_kwargs(severity=None))
        # Falls to the default case (same as normal)
        assert len(report.follow_up) >= 2

    def test_limitations_image_mode(self, svc):
        report = svc.build_template_report(**_template_kwargs(input_mode="image"))
        assert any("图像" in lim for lim in report.limitations)

    def test_limitations_signal_mode_no_image_warning(self, svc):
        report = svc.build_template_report(**_template_kwargs(input_mode="signal"))
        assert not any("图像" in lim for lim in report.limitations)

    def test_limitations_low_confidence_triggers_threshold_warning(self, svc):
        report = svc.build_template_report(**_template_kwargs(confidence=0.5))
        assert any("阈值" in lim or "置信度" in lim for lim in report.limitations)

    def test_limitations_high_confidence_no_threshold_warning(self, svc):
        report = svc.build_template_report(**_template_kwargs(confidence=0.9))
        assert not any("阈值" in lim or "置信度" in lim for lim in report.limitations)

    def test_limitations_always_has_base_disclaimer(self, svc):
        report = svc.build_template_report(**_template_kwargs())
        assert len(report.limitations) >= 2
        assert any("不能替代" in lim for lim in report.limitations)


class TestBuildConfidencePhrase:
    """Tests for _build_confidence_phrase boundary thresholds."""

    def test_high_confidence(self, svc):
        phrase = svc._build_confidence_phrase(0.90)
        assert "较强" in phrase

    def test_medium_high_confidence(self, svc):
        phrase = svc._build_confidence_phrase(0.75)
        assert "中等偏高" in phrase

    def test_medium_confidence(self, svc):
        phrase = svc._build_confidence_phrase(0.55)
        assert "不确定性" in phrase

    def test_low_confidence(self, svc):
        phrase = svc._build_confidence_phrase(0.3)
        assert "谨慎" in phrase

    def test_exact_threshold_085(self, svc):
        # At exactly 0.85, should be "high" tier
        phrase = svc._build_confidence_phrase(0.85)
        assert "较强" in phrase

    def test_exact_threshold_070(self, svc):
        # At exactly 0.70, should be "medium-high" tier
        phrase = svc._build_confidence_phrase(0.70)
        assert "中等偏高" in phrase

    def test_exact_threshold_050(self, svc):
        # At exactly 0.50, should be "medium" tier
        phrase = svc._build_confidence_phrase(0.50)
        assert "不确定性" in phrase


# ===========================================================================
# Output parser
# ===========================================================================


class TestStripMarkdownFences:
    """Tests for DiagnosisReportService._strip_markdown_fences()."""

    def test_plain_json(self, svc):
        text = '{"summary": "test"}'
        assert svc._strip_markdown_fences(text) == text

    def test_json_with_backtick_fence(self, svc):
        text = '```json\n{"summary": "test"}\n```'
        result = svc._strip_markdown_fences(text)
        assert result == '{"summary": "test"}'

    def test_json_with_plain_backticks(self, svc):
        text = '```\n{"summary": "test"}\n```'
        result = svc._strip_markdown_fences(text)
        assert result == '{"summary": "test"}'

    def test_whitespace_around(self, svc):
        text = '  \n ```json\n{"summary": "test"}\n``` \n '
        result = svc._strip_markdown_fences(text)
        assert result == '{"summary": "test"}'

    def test_no_closing_fence(self, svc):
        text = '```json\n{"summary": "test"}'
        result = svc._strip_markdown_fences(text)
        assert result == '{"summary": "test"}'

    def test_empty_string(self, svc):
        assert svc._strip_markdown_fences("") == ""

    def test_only_whitespace(self, svc):
        assert svc._strip_markdown_fences("   \n  ") == ""


class TestParseLLMText:
    """Tests for DiagnosisReportService._parse_llm_text()."""

    def _fallback(self) -> DiagnosisEnhancedReport:
        return DiagnosisEnhancedReport(
            source="template",
            summary="Fallback summary",
            clinical_interpretation="Fallback interpretation",
            key_findings=["Fallback finding"],
            recommendations=["Fallback rec"],
            follow_up=["Fallback follow-up"],
            limitations=["Fallback limitation"],
        )

    def test_valid_json_returns_llm_report(self, svc):
        fallback = self._fallback()
        raw = json.dumps({
            "summary": "LLM summary",
            "clinical_interpretation": "LLM interp",
            "key_findings": ["Finding 1"],
            "recommendations": ["Rec 1"],
            "follow_up": ["FU 1"],
            "limitations": ["Lim 1"],
        })
        result = svc._parse_llm_text(raw, "test-model", fallback, "Test")
        assert result is not None
        assert result.source == "llm"
        assert result.model == "test-model"
        assert result.summary == "LLM summary"

    def test_json_with_markdown_fences(self, svc):
        fallback = self._fallback()
        raw = '```json\n{"summary": "S", "clinical_interpretation": "CI"}\n```'
        result = svc._parse_llm_text(raw, "model", fallback, "Test")
        assert result is not None
        assert result.source == "llm"

    def test_invalid_json_returns_none(self, svc):
        fallback = self._fallback()
        result = svc._parse_llm_text("not json at all", "model", fallback, "Test")
        assert result is None

    def test_extra_fields_returns_none(self, svc):
        fallback = self._fallback()
        raw = json.dumps({
            "summary": "S",
            "clinical_interpretation": "CI",
            "extra_field": "should fail",
        })
        # _LLMReportBody has extra="forbid"
        result = svc._parse_llm_text(raw, "model", fallback, "Test")
        assert result is None

    def test_partial_fields_uses_fallback(self, svc):
        fallback = self._fallback()
        raw = json.dumps({
            "summary": "LLM summary",
            "clinical_interpretation": "LLM interp",
            "key_findings": [],
            "recommendations": [],
            "follow_up": [],
            "limitations": [],
        })
        result = svc._parse_llm_text(raw, "model", fallback, "Test")
        assert result is not None
        # Empty lists should fall back to fallback values
        assert result.key_findings == fallback.key_findings
        assert result.recommendations == fallback.recommendations

    def test_minimal_valid_json(self, svc):
        fallback = self._fallback()
        raw = json.dumps({"summary": "S", "clinical_interpretation": "CI"})
        result = svc._parse_llm_text(raw, "model", fallback, "Test")
        assert result is not None
        assert result.summary == "S"


class TestLLMReportBody:
    """Tests for the _LLMReportBody Pydantic schema."""

    def test_accepts_minimal_fields(self):
        body = _LLMReportBody(summary="S", clinical_interpretation="CI")
        assert body.summary == "S"

    def test_accepts_all_fields(self):
        body = _LLMReportBody(
            summary="S",
            clinical_interpretation="CI",
            key_findings=["F1"],
            recommendations=["R1"],
            follow_up=["FU1"],
            limitations=["L1"],
        )
        assert len(body.key_findings) == 1

    def test_rejects_extra_fields(self):
        with pytest.raises(Exception):
            _LLMReportBody(
                summary="S",
                clinical_interpretation="CI",
                unknown_field="oops",
            )

    def test_defaults_to_empty_lists(self):
        body = _LLMReportBody(summary="S", clinical_interpretation="CI")
        assert body.key_findings == []
        assert body.recommendations == []


# ===========================================================================
# generate_report (coordinator)
# ===========================================================================


class TestGenerateReport:
    """Tests for DiagnosisReportService.generate_report() coordinator."""

    def test_returns_template_when_llm_disabled(self, svc):
        with patch.object(settings, "LLM_REPORT_ENABLED", False):
            report = asyncio.run(svc.generate_report(**_generate_kwargs()))
        assert report.source == "template"

    def test_returns_template_when_openai_no_key(self, svc):
        with (
            patch.object(settings, "LLM_REPORT_ENABLED", True),
            patch.object(settings, "LLM_REPORT_PROVIDER", "openai"),
            patch.object(settings, "OPENAI_API_KEY", None),
        ):
            report = asyncio.run(svc.generate_report(**_generate_kwargs()))
        assert report.source == "template"

    def test_returns_template_when_anthropic_no_key(self, svc):
        with (
            patch.object(settings, "LLM_REPORT_ENABLED", True),
            patch.object(settings, "LLM_REPORT_PROVIDER", "anthropic_compatible"),
            patch.object(settings, "ANTHROPIC_COMPAT_API_KEY", None),
        ):
            report = asyncio.run(svc.generate_report(**_generate_kwargs()))
        assert report.source == "template"

    def test_returns_template_for_unsupported_provider(self, svc):
        with (
            patch.object(settings, "LLM_REPORT_ENABLED", True),
            patch.object(settings, "LLM_REPORT_PROVIDER", "nonexistent"),
        ):
            report = asyncio.run(svc.generate_report(**_generate_kwargs()))
        assert report.source == "template"

    def test_falls_back_to_template_on_llm_exception(self, svc):
        with (
            patch.object(settings, "LLM_REPORT_ENABLED", True),
            patch.object(settings, "LLM_REPORT_PROVIDER", "openai"),
            patch.object(settings, "OPENAI_API_KEY", "test-key"),
        ):
            with patch.object(
                svc, "_generate_with_openai", new_callable=AsyncMock
            ) as mock_gen:
                mock_gen.side_effect = RuntimeError("LLM down")
                report = asyncio.run(svc.generate_report(**_generate_kwargs()))
        assert report.source == "template"

    def test_falls_back_to_template_when_llm_returns_none(self, svc):
        with (
            patch.object(settings, "LLM_REPORT_ENABLED", True),
            patch.object(settings, "LLM_REPORT_PROVIDER", "openai"),
            patch.object(settings, "OPENAI_API_KEY", "test-key"),
            patch.object(
                svc, "_generate_with_openai", new_callable=AsyncMock, return_value=None
            ),
        ):
            report = asyncio.run(svc.generate_report(**_generate_kwargs()))
        assert report.source == "template"

    def test_returns_llm_report_on_success(self, svc):
        llm_report = DiagnosisEnhancedReport(
            source="llm",
            model="gpt-4o-mini",
            summary="Enhanced summary",
            clinical_interpretation="Enhanced interp",
        )
        with (
            patch.object(settings, "LLM_REPORT_ENABLED", True),
            patch.object(settings, "LLM_REPORT_PROVIDER", "openai"),
            patch.object(settings, "OPENAI_API_KEY", "test-key"),
            patch.object(
                svc, "_generate_with_openai", new_callable=AsyncMock, return_value=llm_report
            ),
        ):
            report = asyncio.run(svc.generate_report(**_generate_kwargs()))
        assert report.source == "llm"
        assert report.model == "gpt-4o-mini"

    def test_passes_relevant_kwargs_to_template_builder(self, svc):
        """generate_report passes template-relevant params through to build_template_report."""
        kwargs = _generate_kwargs()
        with (
            patch.object(settings, "LLM_REPORT_ENABLED", False),
            patch.object(svc, "build_template_report", wraps=svc.build_template_report) as spy,
        ):
            asyncio.run(svc.generate_report(**kwargs))
        # build_template_report doesn't receive all_probabilities
        expected_call_kwargs = {k: v for k, v in kwargs.items() if k != "all_probabilities"}
        spy.assert_called_once_with(**expected_call_kwargs)

    def test_anthropic_provider_alias_zhipu(self, svc):
        """zhipu_anthropic provider uses _generate_with_anthropic_compatible."""
        with (
            patch.object(settings, "LLM_REPORT_ENABLED", True),
            patch.object(settings, "LLM_REPORT_PROVIDER", "zhipu_anthropic"),
            patch.object(settings, "ANTHROPIC_COMPAT_API_KEY", "test-key"),
            patch.object(
                svc, "_generate_with_anthropic_compatible", new_callable=AsyncMock, return_value=None
            ) as mock_gen,
        ):
            asyncio.run(svc.generate_report(**_generate_kwargs()))
        mock_gen.assert_called_once()


# ===========================================================================
# Singleton
# ===========================================================================


class TestGetDiagnosisReportService:
    def test_returns_same_instance(self):
        a = get_diagnosis_report_service()
        b = get_diagnosis_report_service()
        assert a is b

    def test_returns_diagnosis_report_service(self):
        svc = get_diagnosis_report_service()
        assert isinstance(svc, DiagnosisReportService)
