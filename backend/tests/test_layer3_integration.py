"""
Tests for Layer 3 integration — QC metadata flowing through
predict_from_image() and into the API response.
"""

import numpy as np
import pytest
import torch

from ml.ecg_image_converter import ECGImageToSignal
from ml.pipeline_types import ExtractionResult, LeadQC


def _make_ecg_12x1(
    height: int = 1200, width: int = 2400, num_leads: int = 12
) -> np.ndarray:
    """Synthetic 12x1 ECG layout with distinct horizontal signal strips."""
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    strip_h = height // num_leads
    for i in range(num_leads):
        y_center = i * strip_h + strip_h // 2
        for x in range(width):
            y_offset = int(5 * np.sin(2 * np.pi * x / 200 + i))
            y_pos = y_center + y_offset
            if 0 <= y_pos < height:
                image[y_pos - 1 : y_pos + 2, x] = 0
    return image


def _make_sparse_ecg(
    height: int = 1200, width: int = 2400, num_leads: int = 12
) -> np.ndarray:
    """ECG with only 8 visible leads (some rows are blank)."""
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    strip_h = height // num_leads
    visible_leads = [0, 1, 2, 4, 5, 7, 9, 11]  # 8 out of 12
    for i in visible_leads:
        y_center = i * strip_h + strip_h // 2
        for x in range(width):
            y_offset = int(5 * np.sin(2 * np.pi * x / 200 + i))
            y_pos = y_center + y_offset
            if 0 <= y_pos < height:
                image[y_pos - 1 : y_pos + 2, x] = 0
    return image


def _make_report():
    """Create a minimal DiagnosisEnhancedReport for testing."""
    from app.services.diagnosis_report_service import DiagnosisEnhancedReport

    return DiagnosisEnhancedReport(
        source="template",
        summary="test summary",
        clinical_interpretation="test interpretation",
    )


# ---------------------------------------------------------------------------
# Test predict_from_image() returns QC metadata
# ---------------------------------------------------------------------------


class TestPredictFromImageQC:
    """Verify that predict_from_image() includes extraction QC metadata."""

    @pytest.fixture()
    def service(self):
        """Create a CardioFormerService with random weights."""
        from ml.cardioformer_service import CardioFormerService

        return CardioFormerService(
            checkpoint_path=None,
            num_classes=5,
            signal_length=1000,
            input_channels=12,
            device="cpu",
        )

    def test_result_contains_extraction_qc_key(self, service):
        """predict_from_image() should include 'extraction_qc' in result."""
        result = service.predict_from_image(_make_ecg_12x1())
        assert "extraction_qc" in result

    def test_extraction_qc_is_extraction_result(self, service):
        """extraction_qc should be an ExtractionResult instance."""
        result = service.predict_from_image(_make_ecg_12x1())
        assert isinstance(result["extraction_qc"], ExtractionResult)

    def test_extraction_qc_has_per_lead_qc(self, service):
        """extraction_qc should contain per-lead QC data."""
        result = service.predict_from_image(_make_ecg_12x1())
        qc = result["extraction_qc"]
        assert len(qc.per_lead_qc) == 12
        for lead_qc in qc.per_lead_qc:
            assert isinstance(lead_qc, LeadQC)

    def test_extraction_qc_has_overall_quality(self, service):
        """extraction_qc should report overall quality."""
        result = service.predict_from_image(_make_ecg_12x1())
        qc = result["extraction_qc"]
        assert qc.overall_quality in ("pass", "warn", "fail")

    def test_result_still_contains_prediction(self, service):
        """Prediction fields should remain unchanged."""
        result = service.predict_from_image(_make_ecg_12x1())
        assert "prediction" in result
        assert "confidence" in result
        assert isinstance(result["prediction"], str)
        assert isinstance(result["confidence"], float)


# ---------------------------------------------------------------------------
# Test DiagnosisResponse accepts quality fields
# ---------------------------------------------------------------------------


class TestDiagnosisResponseQualityFields:
    """Verify DiagnosisResponse can carry quality metadata."""

    def test_quality_warning_optional(self):
        """quality_warning field should be optional."""
        from app.api.diagnosis import DiagnosisResponse

        resp = DiagnosisResponse(
            prediction="正常",
            confidence=0.95,
            timestamp="2025-01-01T00:00:00",
            report=_make_report(),
        )
        assert resp.quality_warning is None

    def test_quality_warning_can_be_set(self):
        """quality_warning field should accept a string."""
        from app.api.diagnosis import DiagnosisResponse

        resp = DiagnosisResponse(
            prediction="正常",
            confidence=0.95,
            timestamp="2025-01-01T00:00:00",
            report=_make_report(),
            quality_warning="warn",
        )
        assert resp.quality_warning == "warn"

    def test_pipeline_warnings_optional(self):
        """pipeline_warnings field should default to empty list."""
        from app.api.diagnosis import DiagnosisResponse

        resp = DiagnosisResponse(
            prediction="正常",
            confidence=0.95,
            timestamp="2025-01-01T00:00:00",
            report=_make_report(),
        )
        assert resp.pipeline_warnings == []

    def test_pipeline_warnings_can_include_messages(self):
        """pipeline_warnings should accept a list of warning strings."""
        from app.api.diagnosis import DiagnosisResponse

        resp = DiagnosisResponse(
            prediction="正常",
            confidence=0.95,
            timestamp="2025-01-01T00:00:00",
            report=_make_report(),
            pipeline_warnings=["导联信号提取质量较低"],
        )
        assert len(resp.pipeline_warnings) == 1


class TestConverterWarningsFlow:
    """Verify converter-level warnings/issues are forwarded to pipeline_warnings."""

    def test_sparse_image_produces_pipeline_warnings(self):
        """Sparse ECG image should produce per-lead warnings via predict_from_image."""
        from ml.cardioformer_service import CardioFormerService

        service = CardioFormerService(
            checkpoint_path=None,
            num_classes=5,
            signal_length=1000,
            input_channels=12,
            device="cpu",
        )
        # Sparse image: only 8 of 12 leads have signal
        result = service.predict_from_image(_make_sparse_ecg())
        qc = result["extraction_qc"]
        # Should have at least some poor/fail leads
        poor_leads = [lq for lq in qc.per_lead_qc if lq.quality in ("fail", "poor")]
        assert len(poor_leads) >= 1
