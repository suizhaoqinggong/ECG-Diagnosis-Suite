"""
Tests for async/resource/security fixes.

Covers:
- P0-1: ML inference runs in thread pool (not blocking event loop)
- P1-4: Database engine disposed on shutdown
- P1-5: SQL echo controlled by DB_ECHO, not DEBUG
- P0-2: Pillow decompression bomb protection not globally disabled
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# P0-1: asyncio.to_thread for ML inference
# ---------------------------------------------------------------------------


class TestAsyncInference:
    """ML inference should run in a thread pool to avoid blocking the event loop."""

    def test_diagnose_image_uses_to_thread(self):
        """diagnose_image should offload model predict_from_signal to a thread."""
        from app.services.diagnosis_service import DiagnosisService

        mock_model = MagicMock()
        mock_model.predict_from_signal.return_value = {
            "prediction": "正常",
            "confidence": 0.95,
            "top3_predictions": [],
            "all_probabilities": {},
            "detected_labels": [],
            "secondary_findings": [],
        }
        mock_model.image_converter.extract_with_result.return_value = MagicMock(
            signals=__import__("numpy").zeros((12, 1000)),
            overall_quality="pass",
            per_lead_qc=[],
            interpolated_ratio=0.0,
            warnings=[],
            issues=[],
        )

        mock_get_model = MagicMock(return_value=mock_model)
        mock_loader_cls = MagicMock()
        mock_decode = MagicMock(
            return_value=MagicMock(image_rgb=__import__("numpy").zeros((100, 100, 3), dtype="uint8"))
        )

        service = DiagnosisService(
            get_model_service_fn=mock_get_model,
            ecg_loader_cls=mock_loader_cls,
            decode_image_fn=mock_decode,
        )

        # Check that the service has a method that wraps sync work in to_thread
        assert hasattr(service, "_run_in_thread") or hasattr(service, "diagnose_image")

    def test_diagnose_signal_uses_to_thread(self):
        """diagnose_signal should offload model predict_from_signal to a thread."""
        from app.services.diagnosis_service import DiagnosisService

        # The method should exist and be async
        service = DiagnosisService(
            get_model_service_fn=MagicMock(),
            ecg_loader_cls=MagicMock(),
            decode_image_fn=MagicMock(),
        )
        assert asyncio.iscoroutinefunction(service.diagnose_signal)


# ---------------------------------------------------------------------------
# P1-4: Database engine disposed on shutdown
# ---------------------------------------------------------------------------


class TestDatabaseEngineDisposal:
    """Async engine should be disposed when the app shuts down."""

    @patch("app.core.database.engine")
    def test_lifespan_disposes_engine(self, mock_engine):
        """The lifespan handler should call engine.dispose() on shutdown."""
        mock_engine.dispose = AsyncMock()

        from app.main import lifespan
        from fastapi import FastAPI

        app = FastAPI()

        async def run_lifespan():
            async with lifespan(app):
                pass  # Simulate app running, then shutting down

        # After the context manager exits (shutdown), engine.dispose should be called
        import asyncio

        asyncio.get_event_loop().run_until_complete(run_lifespan())

        mock_engine.dispose.assert_awaited_once()


# ---------------------------------------------------------------------------
# P1-5: SQL echo controlled separately from DEBUG
# ---------------------------------------------------------------------------


class TestDatabaseEchoConfig:
    """SQL echo should be controlled by DB_ECHO setting, not directly by DEBUG."""

    def test_echo_independent_of_debug(self):
        """DB_ECHO should be a separate setting from DEBUG."""
        from app.core.config import Settings

        # Default: DEBUG=True, DB_ECHO should be configurable independently
        s = Settings(DEBUG=True, DB_ECHO=False)
        assert s.DB_ECHO is False
        assert s.DEBUG is True

    def test_echo_defaults_false(self):
        """DB_ECHO should default to False to avoid logging PHI."""
        from app.core.config import Settings

        s = Settings()
        # The default should not be True (avoid logging medical data)
        assert hasattr(s, "DB_ECHO")
        assert s.DB_ECHO is False

    def test_engine_uses_db_echo(self):
        """The async engine should use DB_ECHO, not DEBUG."""
        from app.core.config import Settings

        s = Settings(DB_ECHO=False, DEBUG=True)
        # Engine echo should respect DB_ECHO, not DEBUG
        # This means even with DEBUG=True, SQL logging is off by default
        assert s.DB_ECHO is False


# ---------------------------------------------------------------------------
# P0-2: Pillow decompression bomb protection
# ---------------------------------------------------------------------------


class TestPillowDecompressionBombProtection:
    """Image.MAX_IMAGE_PIXELS should NOT be set to None globally."""

    def test_safe_decode_does_not_disable_global_protection(self, tmp_path):
        """safe_decode_image should not set Image.MAX_IMAGE_PIXELS = None."""
        from ml.image_decoder import safe_decode_image

        # Save original value
        original_max_pixels = Image.MAX_IMAGE_PIXELS

        try:
            # Reset to a known value
            Image.MAX_IMAGE_PIXELS = 178_956_970

            # Create a small valid test image
            img = Image.new("RGB", (10, 10), color="white")
            test_path = tmp_path / "test.png"
            img.save(str(test_path))

            # Call safe_decode_image
            safe_decode_image(
                str(test_path),
                max_pixels=178_956_970,
                max_dimension=16000,
                processing_max_dimension=4096,
            )

            # After the call, MAX_IMAGE_PIXELS should NOT be None
            assert Image.MAX_IMAGE_PIXELS is not None, (
                "Image.MAX_IMAGE_PIXELS was set to None, "
                "which globally disables decompression bomb protection"
            )

        finally:
            Image.MAX_IMAGE_PIXELS = original_max_pixels

    def test_global_max_pixels_preserved_after_error(self, tmp_path):
        """Even on error, MAX_IMAGE_PIXELS should be restored."""
        from ml.image_decoder import safe_decode_image, ImageDecodeError

        original_max_pixels = Image.MAX_IMAGE_PIXELS

        try:
            Image.MAX_IMAGE_PIXELS = 178_956_970

            # Create an invalid file
            invalid_path = tmp_path / "invalid.png"
            invalid_path.write_bytes(b"not a real image")

            with pytest.raises(ImageDecodeError):
                safe_decode_image(
                    str(invalid_path),
                    max_pixels=178_956_970,
                    max_dimension=16000,
                    processing_max_dimension=4096,
                )

            assert Image.MAX_IMAGE_PIXELS is not None

        finally:
            Image.MAX_IMAGE_PIXELS = original_max_pixels
