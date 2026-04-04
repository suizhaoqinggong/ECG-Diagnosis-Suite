"""
Performance baseline test for the diagnosis pipeline.

Records timing for key stages without asserting strict limits.
Run with: pytest tests/test_performance_baseline.py -v -s

The test prints a timing table to stdout. Use it to establish a baseline
and detect regressions over time.
"""

import io
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import settings


def _make_png_bytes(width=800, height=600):
    """Create a minimal valid PNG file."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def _make_mock_upload_file(content: bytes, filename: str = "test.png"):
    """Create a mock UploadFile."""
    from fastapi import UploadFile
    file = MagicMock(spec=UploadFile)
    file.file = io.BytesIO(content)
    file.filename = filename
    return file


def _make_mock_result(prediction="正常", confidence=0.95):
    """Create a mock model inference result."""
    return {
        "prediction": prediction,
        "confidence": confidence,
        "all_probabilities": {
            "正常": confidence,
            "心肌梗死": 0.02,
            "ST-T改变": 0.01,
            "传导障碍": 0.01,
            "心室肥大": 0.01,
        },
        "top3_predictions": [
            {"label": prediction, "probability": confidence},
            {"label": "心肌梗死", "probability": 0.02},
            {"label": "ST-T改变", "probability": 0.01},
        ],
        "detected_labels": [prediction],
        "secondary_findings": [],
    }


def _make_mock_extraction(signals=None):
    """Create a mock ExtractionResult."""
    if signals is None:
        signals = np.random.randn(12, 1000).astype(np.float32)
    extraction = MagicMock()
    extraction.signals = signals
    extraction.overall_quality = "good"
    extraction.per_lead_qc = []
    extraction.interpolated_ratio = 0.0
    extraction.warnings = []
    extraction.issues = []
    return extraction


# ===========================================================================
# Pipeline stage timing
# ===========================================================================


class TestPerformanceBaseline:
    """Records timing for each pipeline stage. No strict assertions."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        self.tmp_path = tmp_path
        self.timings: dict[str, float] = {}

    def _record(self, stage: str, duration: float):
        self.timings[stage] = duration

    def _print_timings(self):
        print("\n" + "=" * 60)
        print("  Performance Baseline - Stage Timings")
        print("=" * 60)
        for stage, duration in self.timings.items():
            print(f"  {stage:<30s} {duration * 1000:>8.1f} ms")
        print("=" * 60)

    def test_upload_timing(self):
        """Measure file save throughput."""
        from app.core.upload import save_upload

        content = _make_png_bytes(1200, 900)
        file = _make_mock_upload_file(content, "perf_test.png")
        dest = self.tmp_path / "test.png"

        # Warm up
        file.file.seek(0)
        save_upload(file, dest)
        dest.unlink()

        # Measure
        file.file.seek(0)
        t0 = time.perf_counter()
        save_upload(file, dest)
        t_upload = time.perf_counter() - t0

        self._record("upload (800x600 PNG)", t_upload)
        assert dest.exists()
        self._print_timings()

    def test_filename_sanitization_timing(self):
        """Measure filename sanitization throughput."""
        from app.core.upload import sanitize_filename

        filenames = [
            "normal.png", "../../etc/passwd", "心电图报告.jpg",
            "/tmp/secret.dat", "file\x00.png", "a" * 255 + ".png",
        ] * 100  # 600 iterations

        t0 = time.perf_counter()
        for name in filenames:
            try:
                sanitize_filename(name)
            except Exception:
                pass
        t_sanitize = time.perf_counter() - t0

        self._record("sanitize_filename x600", t_sanitize)
        self._print_timings()

    def test_extension_validation_timing(self):
        """Measure extension validation throughput."""
        from app.core.upload import validate_extension

        filenames = [
            "image.png", "photo.jpg", "ecg.jpeg", "signal.dat",
            "header.hea", "bad.exe", "script.py", "README",
        ] * 100  # 800 iterations

        t0 = time.perf_counter()
        for name in filenames:
            try:
                validate_extension(name)
            except Exception:
                pass
        t_validate = time.perf_counter() - t0

        self._record("validate_extension x800", t_validate)
        self._print_timings()

    def test_image_decode_timing(self):
        """Measure image decoding (PIL + downsampling) throughput."""
        content = _make_png_bytes(2000, 1500)
        path = self.tmp_path / "large.png"
        path.write_bytes(content)

        from ml.image_decoder import safe_decode_image

        t0 = time.perf_counter()
        decoded = safe_decode_image(
            str(path),
            max_pixels=settings.IMAGE_MAX_PIXELS,
            max_dimension=settings.IMAGE_MAX_DIMENSION,
            processing_max_dimension=settings.IMAGE_PROCESSING_MAX_DIMENSION,
        )
        t_decode = time.perf_counter() - t0

        self._record("image_decode (2000x1500)", t_decode)
        assert decoded.image_rgb is not None
        self._print_timings()

    def test_signal_quality_analysis_timing(self):
        """Measure signal quality analysis throughput."""
        from ml.signal_quality import analyze_signal_quality

        signal = np.random.randn(12, 1000).astype(np.float32)

        # Warm up
        analyze_signal_quality(signal)

        # Measure
        t0 = time.perf_counter()
        report = analyze_signal_quality(signal)
        t_quality = time.perf_counter() - t0

        self._record("signal_quality (12x1000)", t_quality)
        assert report is not None
        self._print_timings()

    def test_template_report_timing(self):
        """Measure template report generation throughput."""
        from app.services.report import TemplateReportBuilder

        builder = TemplateReportBuilder()
        kwargs = dict(
            prediction="正常",
            confidence=0.95,
            severity="正常",
            icd_code="R00.0",
            description="心电图波形正常",
            recommendations=["定期体检"],
            input_mode="image",
            top3_predictions=[{"label": "正常", "probability": 0.95}],
        )

        # Warm up
        builder.build_report(**kwargs)

        # Measure
        t0 = time.perf_counter()
        for _ in range(100):
            builder.build_report(**kwargs)
        t_report = time.perf_counter() - t0

        self._record("template_report x100", t_report)
        self._record("template_report (single)", t_report / 100)
        self._print_timings()

    def test_full_image_pipeline_timing(self):
        """Measure the full image diagnosis pipeline (with mocked model)."""
        from app.services.diagnosis_service import DiagnosisService

        mock_result = _make_mock_result()
        mock_extraction = _make_mock_extraction()

        # Build mock model service
        mock_model = MagicMock()
        mock_model.predict_from_signal = MagicMock(return_value=mock_result)
        mock_model.image_converter = MagicMock()
        mock_model.image_converter.extract_with_result = MagicMock(
            return_value=mock_extraction
        )

        mock_get_model = MagicMock(return_value=mock_model)

        # Build mock decode function
        decoded = MagicMock()
        decoded.image_rgb = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)
        mock_decode = MagicMock(return_value=decoded)

        service = DiagnosisService(
            get_model_service_fn=mock_get_model,
            ecg_loader_cls=MagicMock(),
            decode_image_fn=mock_decode,
        )

        content = _make_png_bytes(800, 600)
        file = _make_mock_upload_file(content, "baseline.png")

        # Patch report generation to avoid LLM calls
        from app.services.diagnosis_report_service import (
            DiagnosisEnhancedReport,
            get_diagnosis_report_service,
        )

        mock_report = DiagnosisEnhancedReport(
            source="template",
            summary="Test summary",
            clinical_interpretation="Test interpretation",
        )
        mock_report_svc = MagicMock()
        mock_report_svc.generate_report = AsyncMock(return_value=mock_report)

        with patch(
            "app.services.diagnosis_service.get_diagnosis_report_service",
            return_value=mock_report_svc,
        ):
            import asyncio
            t0 = time.perf_counter()
            response = asyncio.run(
                service.diagnose_image(file, "baseline.png", user_id=None)
            )
            t_total = time.perf_counter() - t0

        self._record("full_image_pipeline", t_total)
        assert response.prediction == "正常"
        self._print_timings()

    def test_full_dat_pipeline_timing(self):
        """Measure the full DAT diagnosis pipeline (with mocked model)."""
        from app.services.diagnosis_service import DiagnosisService

        mock_result = _make_mock_result()

        # Build mock model service
        mock_model = MagicMock()
        mock_model.predict_from_signal = MagicMock(return_value=mock_result)
        mock_get_model = MagicMock(return_value=mock_model)

        # Build mock ECG loader
        signal_data = np.random.randn(12, 1000).astype(np.float32)
        mock_loader = MagicMock()
        mock_loader.load_dat_file = MagicMock(
            return_value=(signal_data, {"fs": 500})
        )
        mock_loader.validate_signal = MagicMock(return_value=True)
        mock_loader_cls = MagicMock(return_value=mock_loader)

        service = DiagnosisService(
            get_model_service_fn=mock_get_model,
            ecg_loader_cls=mock_loader_cls,
            decode_image_fn=MagicMock(),
        )

        # Create mock files
        dat_content = b"\x00" * 1000
        hea_content = b"test signal 12 500\n"

        dat_file = _make_mock_upload_file(dat_content, "test.dat")
        hea_file = _make_mock_upload_file(hea_content, "test.hea")

        # Patch report generation
        from app.services.diagnosis_report_service import (
            DiagnosisEnhancedReport,
        )
        mock_report = DiagnosisEnhancedReport(
            source="template",
            summary="Test summary",
            clinical_interpretation="Test interpretation",
        )
        mock_report_svc = MagicMock()
        mock_report_svc.generate_report = AsyncMock(return_value=mock_report)

        with patch(
            "app.services.diagnosis_service.get_diagnosis_report_service",
            return_value=mock_report_svc,
        ):
            import asyncio
            t0 = time.perf_counter()
            response = asyncio.run(
                service.diagnose_dat_pair(
                    dat_file, hea_file, "test.dat", "test.hea", user_id=None
                )
            )
            t_total = time.perf_counter() - t0

        self._record("full_dat_pipeline", t_total)
        assert response.prediction == "正常"
        self._print_timings()
