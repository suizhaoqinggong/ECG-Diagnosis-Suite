"""
Security tests for diagnosis endpoint rate limiting.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app
from app.core.auth_dependencies import get_optional_user
from app.core.rate_limit import rate_limiter


def _mock_user(id=1, email="test@example.com", display_name="Tester"):
    user = MagicMock()
    user.id = id
    user.email = email
    user.display_name = display_name
    user.is_active = True
    return user


def _model_result(prediction="正常", confidence=0.95):
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
        ],
        "detected_labels": [prediction],
        "secondary_findings": [],
    }


def _make_decoded_image():
    from ml.pipeline_types import DecodedImage

    return DecodedImage(
        image_rgb=np.zeros((100, 100, 3), dtype=np.uint8),
        width=100,
        height=100,
        format="PNG",
        mode="RGB",
        exif_transposed=False,
    )


def _make_extraction_result(quality="pass"):
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


def _setup_mock_service(mock_get_service, model_result=None, extraction_quality="pass"):
    """Configure the mock model service with extraction and prediction."""
    if model_result is None:
        model_result = _model_result()
    mock_service = MagicMock()
    mock_service.predict_from_signal.return_value = model_result
    mock_service.image_converter.extract_with_result.return_value = _make_extraction_result(
        quality=extraction_quality
    )
    mock_get_service.return_value = mock_service
    return mock_service


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    rate_limiter.reset()
    yield
    rate_limiter.reset()


IMAGE_FILE = ("ecg.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")


class TestDiagnoseImageRateLimit:
    def test_anonymous_ip_rate_limited(self, client):
        """Anonymous requests are rate-limited to 5/min per IP."""
        async def _anonymous():
            return None

        app.dependency_overrides[get_optional_user] = _anonymous
        try:
            with (
                patch("ml.signal_quality.analyze_signal_quality", return_value=_make_quality_report()),
                patch("app.api.diagnosis.get_model_service") as mock_get_service,
                patch("app.api.diagnosis.safe_decode_image", return_value=_make_decoded_image()),
            ):
                _setup_mock_service(mock_get_service)

                for _ in range(5):
                    response = client.post("/api/diagnose", files={"file": IMAGE_FILE})
                    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

                # 6th request should be rate-limited
                response = client.post("/api/diagnose", files={"file": IMAGE_FILE})
                assert response.status_code == 429
        finally:
            app.dependency_overrides.pop(get_optional_user, None)

    def test_authenticated_user_higher_limit(self, client):
        """Authenticated users get a higher rate limit (30/min)."""
        user = _mock_user()

        async def _authed():
            return user

        app.dependency_overrides[get_optional_user] = _authed
        try:
            with (
                patch("ml.signal_quality.analyze_signal_quality", return_value=_make_quality_report()),
                patch("app.api.diagnosis.get_model_service") as mock_get_service,
                patch("app.api.diagnosis.safe_decode_image", return_value=_make_decoded_image()),
            ):
                _setup_mock_service(mock_get_service)

                # 6 requests should all succeed (limit is 30 for authenticated)
                for _ in range(6):
                    response = client.post("/api/diagnose", files={"file": IMAGE_FILE})
                    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        finally:
            app.dependency_overrides.pop(get_optional_user, None)

    def test_rate_limit_resets_after_window(self, client):
        """After resetting rate limiter, requests should work again."""
        async def _anonymous():
            return None

        app.dependency_overrides[get_optional_user] = _anonymous
        try:
            with (
                patch("ml.signal_quality.analyze_signal_quality", return_value=_make_quality_report()),
                patch("app.api.diagnosis.get_model_service") as mock_get_service,
                patch("app.api.diagnosis.safe_decode_image", return_value=_make_decoded_image()),
            ):
                _setup_mock_service(mock_get_service)

                for _ in range(5):
                    response = client.post("/api/diagnose", files={"file": IMAGE_FILE})
                    assert response.status_code == 200

                # Should be rate limited
                response = client.post("/api/diagnose", files={"file": IMAGE_FILE})
                assert response.status_code == 429

                # Reset rate limiter
                rate_limiter.reset()

                # Should succeed again
                response = client.post("/api/diagnose", files={"file": IMAGE_FILE})
                assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(get_optional_user, None)


class TestDiagnoseDatRateLimit:
    def test_anonymous_ip_rate_limited(self, client):
        """Anonymous requests to /diagnose-dat are rate-limited to 5/min."""
        async def _anonymous():
            return None

        app.dependency_overrides[get_optional_user] = _anonymous
        try:
            with (
                patch("app.api.diagnosis.get_model_service") as mock_get_service,
                patch("app.api.diagnosis.ECGDataLoader") as MockLoader,
            ):
                mock_service = MagicMock()
                mock_service.predict_from_signal.return_value = _model_result()
                mock_get_service.return_value = mock_service

                mock_loader = MockLoader.return_value
                mock_loader.load_dat_file.return_value = (
                    np.zeros((12, 1000), dtype=np.float32),
                    {"fs": 500},
                )
                mock_loader.validate_signal.return_value = True

                dat_files = [
                    ("files", ("record.dat", b"\x00" * 100, "application/octet-stream")),
                    ("files", ("record.hea", b"record 2 500 1000", "text/plain")),
                ]

                for _ in range(5):
                    response = client.post("/api/diagnose-dat", files=dat_files)
                    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

                # 6th request should be rate-limited
                response = client.post("/api/diagnose-dat", files=dat_files)
                assert response.status_code == 429
        finally:
            app.dependency_overrides.pop(get_optional_user, None)

    def test_authenticated_user_higher_limit(self, client):
        """Authenticated users get a higher rate limit for /diagnose-dat."""
        user = _mock_user()

        async def _authed():
            return user

        app.dependency_overrides[get_optional_user] = _authed
        try:
            with (
                patch("app.api.diagnosis.get_model_service") as mock_get_service,
                patch("app.api.diagnosis.ECGDataLoader") as MockLoader,
            ):
                mock_service = MagicMock()
                mock_service.predict_from_signal.return_value = _model_result()
                mock_get_service.return_value = mock_service

                mock_loader = MockLoader.return_value
                mock_loader.load_dat_file.return_value = (
                    np.zeros((12, 1000), dtype=np.float32),
                    {"fs": 500},
                )
                mock_loader.validate_signal.return_value = True

                dat_files = [
                    ("files", ("record.dat", b"\x00" * 100, "application/octet-stream")),
                    ("files", ("record.hea", b"record 2 500 1000", "text/plain")),
                ]

                for _ in range(6):
                    response = client.post("/api/diagnose-dat", files=dat_files)
                    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        finally:
            app.dependency_overrides.pop(get_optional_user, None)
