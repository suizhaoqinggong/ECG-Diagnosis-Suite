"""
Protective tests for diagnosis API endpoints.

Locks in current behavior of /api/diagnose and /api/diagnose-dat
before the planned service extraction refactoring (P0-2 in optimization-plan.md).

These are characterization tests: they verify the CURRENT behavior so that
refactoring does not silently change it.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app
from app.core.rate_limit import rate_limiter


# ===== Fixtures =====


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


@pytest.fixture
def client():
    with TestClient(app) as tc:
        yield tc


def _model_result(prediction="正常", confidence=0.95):
    """Build a standard model prediction result matching CardioFormer output."""
    return {
        "prediction": prediction,
        "prediction_en": "NORM",
        "confidence": confidence,
        "class_index": 0,
        "all_probabilities": {
            "正常": confidence,
            "心肌梗死": 0.01,
            "ST-T改变": 0.02,
            "传导障碍": 0.01,
            "心室肥大": 0.01,
        },
        "top3_predictions": [
            {"class": prediction, "class_en": "NORM", "probability": confidence},
            {"class": "ST-T改变", "class_en": "STTC", "probability": 0.02},
            {"class": "心肌梗死", "class_en": "MI", "probability": 0.01},
        ],
        "detected_labels": [prediction],
        "secondary_findings": [],
    }


def _make_extraction_result(quality="pass"):
    """Build a mock ExtractionResult with realistic defaults."""
    from ml.pipeline_types import ExtractionResult, LeadQC

    return ExtractionResult(
        signals=np.random.randn(12, 1000).astype(np.float32) * 0.1,
        layout_method="12x1",
        layout_score=0.9,
        fallback_used=False,
        interpolated_columns=0,
        interpolated_ratio=0.0,
        per_lead_qc=[
            LeadQC(
                lead_index=i,
                flatness=0.1,
                coverage=0.95,
                valid_column_ratio=0.95,
                interpolated_ratio=0.0,
                jump_rate=0.01,
                clipped_ratio=0.0,
                snr_estimate=10.0,
                quality="good",
            )
            for i in range(12)
        ],
        warnings=[],
        issues=[],
        overall_quality=quality,
    )


def _make_quality_report(collapsed=False):
    """Build a mock SignalQualityReport."""
    from ml.signal_quality import SignalQualityReport

    if collapsed:
        return SignalQualityReport(
            mean_correlation=0.99,
            max_correlation=1.0,
            high_corr_ratio=1.0,
            flat_lead_count=12,
            is_collapsed=True,
            warning="信号质量不足",
        )
    return SignalQualityReport(
        mean_correlation=0.3,
        max_correlation=0.5,
        high_corr_ratio=0.0,
        flat_lead_count=0,
        is_collapsed=False,
        warning=None,
    )


def _make_decoded_image():
    """Build a mock DecodedImage."""
    from ml.pipeline_types import DecodedImage

    return DecodedImage(
        image_rgb=np.zeros((100, 100, 3), dtype=np.uint8),
        width=100,
        height=100,
        format="PNG",
        mode="RGB",
        exif_transposed=False,
    )


# Shared mock context manager for image diagnosis success path
def _mock_image_diagnosis(model_result=None):
    """Return mock patches for the full image diagnosis pipeline."""
    if model_result is None:
        model_result = _model_result()

    return (
        patch("ml.signal_quality.analyze_signal_quality", return_value=_make_quality_report(collapsed=False)),
        patch("app.api.diagnosis.get_model_service"),
        patch("app.api.diagnosis.safe_decode_image", return_value=_make_decoded_image()),
    )


def _setup_mock_service(mock_get_service, model_result, extraction_quality="pass"):
    """Configure the mock model service with extraction and prediction."""
    mock_service = MagicMock()
    mock_service.predict_from_signal.return_value = model_result
    mock_service.image_converter.extract_with_result.return_value = _make_extraction_result(
        quality=extraction_quality
    )
    mock_get_service.return_value = mock_service
    return mock_service


# ===== POST /api/diagnose =====


class TestDiagnoseImage:
    """Tests for POST /api/diagnose (image upload path)."""

    def test_no_file_returns_422(self, client):
        """Missing file field → 422 validation error."""
        response = client.post("/api/diagnose")
        assert response.status_code == 422

    def test_unsupported_file_type(self, client):
        """Non-image, non-dat file → 400."""
        files = {"file": ("test.txt", b"hello", "text/plain")}
        response = client.post("/api/diagnose", files=files)
        assert response.status_code == 400

    def test_dat_file_rejected(self, client):
        """Uploading .dat to /diagnose → 400 with guidance to use /diagnose-dat."""
        files = {"file": ("record.dat", b"\x00" * 100, "application/octet-stream")}
        response = client.post("/api/diagnose", files=files)
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "diagnose-dat" in detail or ".dat" in detail

    def test_success_returns_complete_response(self, client):
        """Valid image → 200 with all expected fields."""
        with (
            patch("ml.signal_quality.analyze_signal_quality", return_value=_make_quality_report(collapsed=False)),
            patch("app.api.diagnosis.get_model_service") as mock_get_service,
            patch("app.api.diagnosis.safe_decode_image", return_value=_make_decoded_image()),
        ):
            _setup_mock_service(mock_get_service, _model_result())

            files = {"file": ("ecg.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")}
            response = client.post("/api/diagnose", files=files)

            assert response.status_code == 200
            data = response.json()

            # All required fields present
            for field in [
                "prediction",
                "confidence",
                "severity",
                "icd_code",
                "description",
                "recommendations",
                "timestamp",
                "all_probabilities",
                "top3_predictions",
                "detected_labels",
                "secondary_findings",
                "quality_warning",
                "pipeline_warnings",
                "report",
                "disclaimer",
            ]:
                assert field in data, f"Missing field: {field}"

            # Types and values
            assert data["prediction"] == "正常"
            assert isinstance(data["confidence"], float)
            assert isinstance(data["timestamp"], str)
            assert len(data["timestamp"]) > 0
            assert isinstance(data["disclaimer"], str)
            assert len(data["disclaimer"]) > 0

    def test_image_extension_is_accepted_even_with_generic_mime_type(self, client):
        """Valid image extension should not depend on client MIME sniffing."""
        with (
            patch("ml.signal_quality.analyze_signal_quality", return_value=_make_quality_report(collapsed=False)),
            patch("app.api.diagnosis.get_model_service") as mock_get_service,
            patch("app.api.diagnosis.safe_decode_image", return_value=_make_decoded_image()),
        ):
            _setup_mock_service(mock_get_service, _model_result())

            files = {"file": ("ecg.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "application/octet-stream")}
            response = client.post("/api/diagnose", files=files)

            assert response.status_code == 200
            assert response.json()["prediction"] == "正常"

    def test_symptom_database_enrichment(self, client):
        """Response includes severity, icd_code, description from SYMPTOM_DATABASE."""
        with (
            patch("ml.signal_quality.analyze_signal_quality", return_value=_make_quality_report(collapsed=False)),
            patch("app.api.diagnosis.get_model_service") as mock_get_service,
            patch("app.api.diagnosis.safe_decode_image", return_value=_make_decoded_image()),
        ):
            _setup_mock_service(mock_get_service, _model_result(prediction="心肌梗死"))

            files = {"file": ("ecg.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")}
            response = client.post("/api/diagnose", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["severity"] == "严重"
            assert data["icd_code"] == "I21.0"
            assert data["description"] is not None
            assert isinstance(data["recommendations"], list)
            assert len(data["recommendations"]) > 0

    def test_quality_gate_collapsed_skips_inference(self, client):
        """Collapsed signal → 200 with quality warning, no model inference."""
        with (
            patch("ml.signal_quality.analyze_signal_quality", return_value=_make_quality_report(collapsed=True)),
            patch("app.api.diagnosis.get_model_service") as mock_get_service,
            patch("app.api.diagnosis.safe_decode_image", return_value=_make_decoded_image()),
        ):
            mock_service = MagicMock()
            mock_service.image_converter.extract_with_result.return_value = _make_extraction_result(quality="fail")
            mock_get_service.return_value = mock_service

            files = {"file": ("ecg.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")}
            response = client.post("/api/diagnose", files=files)

            assert response.status_code == 200
            data = response.json()

            # Should NOT have run model inference
            assert data["prediction"] == "信号质量不足"
            assert data["confidence"] == 0.0
            assert data["severity"] is None
            assert data["icd_code"] is None
            mock_service.predict_from_signal.assert_not_called()

            # Quality feedback present
            assert len(data["pipeline_warnings"]) > 0

    def test_model_failure_returns_500(self, client):
        """Model inference exception → 500."""
        with (
            patch("ml.signal_quality.analyze_signal_quality", return_value=_make_quality_report(collapsed=False)),
            patch("app.api.diagnosis.get_model_service") as mock_get_service,
            patch("app.api.diagnosis.safe_decode_image", return_value=_make_decoded_image()),
        ):
            mock_service = MagicMock()
            mock_service.image_converter.extract_with_result.return_value = _make_extraction_result()
            mock_service.predict_from_signal.side_effect = RuntimeError("Model crashed")
            mock_get_service.return_value = mock_service

            files = {"file": ("ecg.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")}
            response = client.post("/api/diagnose", files=files)

            assert response.status_code == 500


# ===== POST /api/diagnose-dat =====


class TestDiagnoseDatPair:
    """Tests for POST /api/diagnose-dat (dat + hea pair upload)."""

    def test_wrong_file_count_one_file(self, client):
        """Only one file → 400."""
        files = [("files", ("record.dat", b"\x00" * 100, "application/octet-stream"))]
        response = client.post("/api/diagnose-dat", files=files)
        assert response.status_code == 400

    def test_wrong_file_count_three_files(self, client):
        """Three files → 400."""
        files = [
            ("files", ("a.dat", b"\x00", "application/octet-stream")),
            ("files", ("a.hea", b"hea", "text/plain")),
            ("files", ("extra.txt", b"x", "text/plain")),
        ]
        response = client.post("/api/diagnose-dat", files=files)
        assert response.status_code == 400

    def test_missing_dat_file(self, client):
        """Two .hea files, no .dat → 400."""
        files = [
            ("files", ("a.hea", b"hea1", "text/plain")),
            ("files", ("b.hea", b"hea2", "text/plain")),
        ]
        response = client.post("/api/diagnose-dat", files=files)
        assert response.status_code == 400

    def test_missing_hea_file(self, client):
        """Two .dat files, no .hea → 400."""
        files = [
            ("files", ("a.dat", b"\x00", "application/octet-stream")),
            ("files", ("b.dat", b"\x00", "application/octet-stream")),
        ]
        response = client.post("/api/diagnose-dat", files=files)
        assert response.status_code == 400

    def test_filename_mismatch(self, client):
        """Dat and hea with different basenames → 400."""
        files = [
            ("files", ("patient1.dat", b"\x00" * 100, "application/octet-stream")),
            ("files", ("patient2.hea", b"hea content", "text/plain")),
        ]
        response = client.post("/api/diagnose-dat", files=files)
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "文件名" in detail or "相同" in detail

    def test_success_returns_complete_response(self, client):
        """Valid matched dat+hea pair → 200 with all expected fields."""
        with (
            patch("app.api.diagnosis.get_model_service") as mock_get_service,
            patch("app.api.diagnosis.ECGDataLoader") as MockLoader,
        ):
            # Configure mock loader
            mock_loader = MockLoader.return_value
            mock_loader.load_dat_file.return_value = (
                np.zeros((12, 1000), dtype=np.float32),
                {"fs": 500},
            )
            mock_loader.validate_signal.return_value = True

            # Configure mock model service
            mock_service = MagicMock()
            mock_service.predict_from_signal.return_value = _model_result()
            mock_get_service.return_value = mock_service

            files = [
                ("files", ("record.dat", b"\x00" * 100, "application/octet-stream")),
                ("files", ("record.hea", b"record 2 500 1000", "text/plain")),
            ]
            response = client.post("/api/diagnose-dat", files=files)

            assert response.status_code == 200
            data = response.json()

            # Response structure
            for field in [
                "prediction",
                "confidence",
                "severity",
                "icd_code",
                "timestamp",
                "disclaimer",
                "report",
            ]:
                assert field in data, f"Missing field: {field}"

            assert data["prediction"] == "正常"
            assert isinstance(data["confidence"], float)
            assert data["severity"] == "正常"
            assert data["icd_code"] == "R00.0"

    def test_invalid_signal_returns_400(self, client):
        """Signal validation fails → 400."""
        with (
            patch("app.api.diagnosis.get_model_service") as mock_get_service,
            patch("app.api.diagnosis.ECGDataLoader") as MockLoader,
        ):
            mock_loader = MockLoader.return_value
            mock_loader.load_dat_file.return_value = (
                np.zeros((12, 1000), dtype=np.float32),
                {"fs": 500},
            )
            mock_loader.validate_signal.return_value = False
            mock_get_service.return_value = MagicMock()

            files = [
                ("files", ("record.dat", b"\x00" * 100, "application/octet-stream")),
                ("files", ("record.hea", b"record 2 500 1000", "text/plain")),
            ]
            response = client.post("/api/diagnose-dat", files=files)

            assert response.status_code == 400
            assert "信号" in response.json()["detail"] or "数据" in response.json()["detail"]


# ===== SYMPTOM_DATABASE lookup =====


class TestSymptomDatabase:
    """Verify SYMPTOM_DATABASE maps predictions to correct metadata.

    This protects the data lookup that enriches diagnosis responses.
    If the refactoring extracts this into a service, these mappings
    must be preserved.
    """

    @pytest.mark.parametrize(
        "prediction,expected_severity,expected_icd",
        [
            ("正常", "正常", "R00.0"),
            ("心肌梗死", "严重", "I21.0"),
            ("ST-T改变", "中等", "I20.0"),
            ("传导障碍", "中等", "I44.0"),
            ("心室肥大", "中等", "I42.0"),
        ],
    )
    def test_known_predictions(self, prediction, expected_severity, expected_icd):
        from app.api.diagnosis import SYMPTOM_DATABASE

        entry = SYMPTOM_DATABASE[prediction]
        assert entry["severity"] == expected_severity
        assert entry["icd_code"] == expected_icd
        assert isinstance(entry["description"], str)
        assert len(entry["description"]) > 0
        assert isinstance(entry["recommendations"], list)
        assert len(entry["recommendations"]) > 0

    def test_all_five_categories_present(self):
        from app.api.diagnosis import SYMPTOM_DATABASE

        expected = {"正常", "心肌梗死", "ST-T改变", "传导障碍", "心室肥大"}
        assert set(SYMPTOM_DATABASE.keys()) == expected

    def test_unknown_prediction_returns_empty(self):
        """Prediction not in SYMPTOM_DATABASE → empty dict → None fields."""
        from app.api.diagnosis import SYMPTOM_DATABASE

        result = SYMPTOM_DATABASE.get("未知诊断", {})
        assert result == {}
        assert result.get("severity") is None
        assert result.get("icd_code") is None
