"""
Tests for error leak prevention / sanitization hardening.

Verifies that internal error details (file paths, credentials, stack info)
are NEVER exposed to API clients. Only generic messages are returned in
HTTP responses, while full details are preserved in server-side logs.

TDD: these tests are written BEFORE the implementation. They should FAIL
against the current code and PASS after the hardening changes.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app
from ml.image_decoder import ImageDecodeError, ImageProcessingError


# ===== Shared helpers =====


@pytest.fixture
def client():
    with TestClient(app) as tc:
        yield tc


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


def _make_quality_report():
    """Build a mock SignalQualityReport (non-collapsed)."""
    from ml.signal_quality import SignalQualityReport

    return SignalQualityReport(
        mean_correlation=0.3,
        max_correlation=0.5,
        high_corr_ratio=0.0,
        flat_lead_count=0,
        is_collapsed=False,
        warning=None,
    )


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
            {"class": "ST-T改变", "class_en": "STTC", "probability": 0.02},
            {"class": "心肌梗死", "class_en": "MI", "probability": 0.01},
        ],
        "detected_labels": [prediction],
        "secondary_findings": [],
    }


# ===== TestHealthEndpointInfoLeak =====


class TestHealthEndpointInfoLeak:
    """Verify /health never leaks raw DB error strings to clients."""

    def test_health_returns_sanitized_db_error(self, client):
        """When DB is unavailable, /health must NOT return raw exception strings."""
        from app.core.database import mark_db_unavailable

        # Simulate a DB error that contains credentials in its message
        try:
            raise OperationalError(
                "connection refused at mysql://admin:s3cret@db:3306/ecg"
            )
        except OperationalError as exc:
            mark_db_unavailable(exc)

        response = client.get("/health")
        data = response.json()

        # The error field must NOT contain raw exception details
        error_field = data["database"]["error"]
        assert error_field is not None, "Expected an error field when DB is unavailable"

        # Must not contain credentials or raw details
        assert "s3cret" not in error_field
        assert "mysql://admin" not in error_field
        assert "connection refused" not in error_field

    def test_health_returns_generic_error_message(self, client):
        """When DB is unavailable, /health should return 'database unavailable'."""
        from app.core.database import mark_db_unavailable

        try:
            raise OperationalError(
                "connection refused at mysql://admin:s3cret@db:3306/ecg"
            )
        except OperationalError as exc:
            mark_db_unavailable(exc)

        response = client.get("/health")
        data = response.json()

        error_field = data["database"]["error"]
        assert error_field == "database unavailable"


# Stand-in for SQLAlchemy OperationalError (we don't need the real class)
class OperationalError(Exception):
    pass


# ===== TestDiagnosisServiceErrorSanitization =====


class TestDiagnosisServiceErrorSanitization:
    """Verify diagnosis endpoints return generic error messages,
    never leaking internal details."""

    def test_image_decode_error_sanitized(self, client):
        """ImageDecodeError details must NOT appear in the 400 response."""
        with (
            patch("app.api.diagnosis.safe_decode_image") as mock_decode,
        ):
            mock_decode.side_effect = ImageDecodeError(
                "EXIF overflow at offset 0xDEADBEEF"
            )

            files = {"file": ("ecg.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")}
            response = client.post("/api/diagnose", files=files)

            assert response.status_code == 400
            detail = response.json()["detail"]

            # Must NOT contain raw error internals
            assert "EXIF overflow" not in detail
            assert "0xDEADBEEF" not in detail

            # Must be a generic message
            assert "图像文件无效或损坏" in detail

    def test_image_processing_error_sanitized(self, client):
        """ImageProcessingError details must NOT appear in the 500 response."""
        with (
            patch("app.api.diagnosis.safe_decode_image") as mock_decode,
        ):
            mock_decode.side_effect = ImageProcessingError(
                "PIL decompression bomb threshold exceeded"
            )

            files = {"file": ("ecg.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")}
            response = client.post("/api/diagnose", files=files)

            assert response.status_code == 500
            detail = response.json()["detail"]

            # Must NOT contain raw error internals
            assert "PIL" not in detail
            assert "decompression bomb" not in detail

            # Must be a generic message
            assert "图像处理失败" in detail

    def test_image_diagnosis_catchall_sanitized(self, client):
        """Unexpected RuntimeError during image diagnosis must not leak details."""
        with (
            patch("ml.signal_quality.analyze_signal_quality", return_value=_make_quality_report()),
            patch("app.api.diagnosis.get_model_service") as mock_get_service,
            patch("app.api.diagnosis.safe_decode_image", return_value=_make_decoded_image()),
        ):
            mock_service = MagicMock()
            mock_service.image_converter.extract_with_result.return_value = _make_extraction_result()
            mock_service.predict_from_signal.side_effect = RuntimeError(
                "CUDA out of memory at /tmp/model_weights.bin"
            )
            mock_get_service.return_value = mock_service

            files = {"file": ("ecg.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "image/png")}
            response = client.post("/api/diagnose", files=files)

            assert response.status_code == 500
            detail = response.json()["detail"]

            # Must NOT contain internal details
            assert "CUDA" not in detail
            assert "/tmp/model_weights.bin" not in detail
            assert "out of memory" not in detail

            # Must be a generic message
            assert "诊断失败" in detail

    def test_dat_file_not_found_sanitized(self, client):
        """FileNotFoundError in dat loader must NOT leak file paths."""
        with (
            patch("app.api.diagnosis.get_model_service") as mock_get_service,
            patch("app.api.diagnosis.ECGDataLoader") as MockLoader,
        ):
            mock_loader = MockLoader.return_value
            mock_loader.load_dat_file.side_effect = FileNotFoundError(
                "No .hea file for /data/uploads/session_20240101/record.dat"
            )
            mock_get_service.return_value = MagicMock()

            files = [
                ("files", ("record.dat", b"\x00" * 100, "application/octet-stream")),
                ("files", ("record.hea", b"record 2 500 1000", "text/plain")),
            ]
            response = client.post("/api/diagnose-dat", files=files)

            assert response.status_code == 400
            detail = response.json()["detail"]

            # Must NOT contain internal file paths
            assert "/data/uploads/session_20240101" not in detail
            assert "record.dat" not in detail

            # Must be a generic message
            assert "缺少配套文件" in detail

    def test_dat_diagnosis_catchall_sanitized(self, client):
        """Unexpected exception during dat diagnosis must not leak internal details."""
        with (
            patch("app.api.diagnosis.get_model_service") as mock_get_service,
            patch("app.api.diagnosis.ECGDataLoader") as MockLoader,
        ):
            mock_loader = MockLoader.return_value
            mock_loader.load_dat_file.side_effect = RuntimeError(
                "signal processing failed: shape mismatch [12,500] vs [12,1000]"
            )
            mock_get_service.return_value = MagicMock()

            files = [
                ("files", ("record.dat", b"\x00" * 100, "application/octet-stream")),
                ("files", ("record.hea", b"record 2 500 1000", "text/plain")),
            ]
            response = client.post("/api/diagnose-dat", files=files)

            assert response.status_code == 500
            detail = response.json()["detail"]

            # Must NOT contain internal details
            assert "shape mismatch" not in detail
            assert "[12,500]" not in detail
            assert "[12,1000]" not in detail

            # Must be a generic message
            assert "诊断失败" in detail


# ===== TestDatabaseStartupSanitization =====


class TestDatabaseStartupSanitization:
    """Verify database module masks credentials in log output."""

    def test_startup_log_masks_credentials(self):
        """init_db() must mask password when logging DATABASE_URL."""
        with (
            patch("app.core.database.settings") as mock_settings,
            patch("app.core.database.engine") as mock_engine,
            patch("app.core.database._get_base") as mock_get_base,
            patch("app.core.database.logger") as mock_logger,
        ):
            # Set a DATABASE_URL with credentials
            mock_settings.DATABASE_URL = (
                "mysql+aiomysql://admin:hunter2@db:3306/ecg"
            )
            mock_settings.DEBUG = False
            mock_settings.is_production = False

            # Mock the DB init so it doesn't actually connect
            mock_base = MagicMock()
            mock_get_base.return_value = mock_base

            # Mock engine.begin() async context manager
            mock_conn = AsyncMock()
            mock_conn.run_sync = AsyncMock(return_value={"alembic_version"})
            mock_engine.begin = MagicMock()
            mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)

            import asyncio
            from app.core.database import init_db

            asyncio.get_event_loop().run_until_complete(init_db())

            # Find the logger.info call that logs the DATABASE_URL
            info_calls = mock_logger.info.call_args_list
            assert len(info_calls) > 0, "Expected at least one logger.info call"

            # Check that no call contains the raw password
            for call in info_calls:
                for arg in call[0]:
                    assert "hunter2" not in str(arg), (
                        f"Password leaked in log: {arg}"
                    )
                    assert "admin:hunter2" not in str(arg), (
                        f"User:password leaked in log: {arg}"
                    )

            # Check that masked version IS present
            url_logged = False
            for call in info_calls:
                for arg in call[0]:
                    if "DATABASE_URL" in str(arg) or "mysql" in str(arg):
                        url_logged = True
                        assert "admin:***@" in str(arg) or "hunter2" not in str(arg)
            assert url_logged, "Expected DATABASE_URL to be logged (masked)"
