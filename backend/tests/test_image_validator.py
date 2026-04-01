"""
Tests for image_validator module - ECG image input validation.

Layer 1 of ECG Image Pipeline Hardening:
- Hard-rejects clearly non-ECG images (blank, noise, extreme aspect ratio)
- Soft-warns on borderline quality (density, few content bands)
- Accepts standard ECG layouts (12x1, 3x4)
"""

import numpy as np
import pytest

from ml.image_validator import validate_ecg_image
from ml.pipeline_types import PipelineIssue, ValidationMetrics, ValidationResult


# ---------------------------------------------------------------------------
# Helpers to synthesize test images
# ---------------------------------------------------------------------------


def _make_blank_white(height: int = 800, width: int = 1200) -> np.ndarray:
    """Pure white image."""
    return np.full((height, width, 3), 255, dtype=np.uint8)


def _make_blank_black(height: int = 800, width: int = 1200) -> np.ndarray:
    """Pure black image."""
    return np.zeros((height, width, 3), dtype=np.uint8)


def _make_random_noise(height: int = 800, width: int = 1200) -> np.ndarray:
    """Random noise image."""
    rng = np.random.default_rng(42)
    return rng.integers(0, 255, (height, width, 3), dtype=np.uint8)


def _make_ecg_12x1(
    height: int = 1200, width: int = 2400, num_leads: int = 12
) -> np.ndarray:
    """Synthetic 12x1 ECG layout: 12 horizontal signal strips on white background."""
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


def _make_ecg_3x4(
    height: int = 1200, width: int = 900, rows: int = 4, cols: int = 3
) -> np.ndarray:
    """Synthetic 3x4 ECG layout: 4 rows x 3 columns of signal strips."""
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    strip_h = height // rows
    strip_w = width // cols
    for r in range(rows):
        for c in range(cols):
            y_center = r * strip_h + strip_h // 2
            x_start = c * strip_w
            for x in range(strip_w):
                y_offset = int(4 * np.sin(2 * np.pi * x / 150 + r * cols + c))
                y_pos = y_center + y_offset
                if 0 <= y_pos < height:
                    image[y_pos - 1 : y_pos + 2, x_start + x] = 0
    return image


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestRejectsNonECG:
    """Hard-rejection of clearly non-ECG images."""

    def test_rejects_blank_white(self):
        result = validate_ecg_image(_make_blank_white())
        assert result.accepted is False
        assert any(i.severity == "error" for i in result.issues)

    def test_rejects_blank_black(self):
        result = validate_ecg_image(_make_blank_black())
        assert result.accepted is False
        assert any(i.severity == "error" for i in result.issues)

    def test_rejects_random_noise(self):
        result = validate_ecg_image(_make_random_noise())
        assert result.accepted is False
        assert any(i.severity == "error" for i in result.issues)

    def test_rejects_extreme_aspect_ratio_narrow(self):
        image = np.full((800, 100, 3), 255, dtype=np.uint8)
        image[100:700, :, :] = 0
        result = validate_ecg_image(image)
        assert result.accepted is False
        assert any(i.code == "aspect_ratio_out_of_range" for i in result.issues)

    def test_rejects_extreme_aspect_ratio_wide(self):
        image = np.full((100, 800, 3), 255, dtype=np.uint8)
        image[:, 100:700, :] = 0
        result = validate_ecg_image(image)
        assert result.accepted is False
        assert any(i.code == "aspect_ratio_out_of_range" for i in result.issues)

    def test_rejects_too_small(self):
        image = np.full((300, 800, 3), 255, dtype=np.uint8)
        for y in range(50, 250, 50):
            image[y : y + 3, :] = 0
        result = validate_ecg_image(image)
        assert result.accepted is False
        assert any(i.code == "resolution_too_low" for i in result.issues)


class TestWarnsBorderline:
    """Soft warnings on borderline quality images."""

    def test_warns_few_content_bands(self):
        """Image with only 2 horizontal bands → warning."""
        height, width = 800, 1200
        image = np.full((height, width, 3), 255, dtype=np.uint8)
        # Two thick horizontal bands to ensure they are detected
        image[200:230, :] = 0
        image[600:630, :] = 0
        result = validate_ecg_image(image)
        if result.accepted:
            assert any(i.code == "too_few_content_bands" for i in result.issues)


class TestAcceptsECG:
    """Accepts valid ECG-like images."""

    def test_accepts_standard_12x1_ecg(self):
        result = validate_ecg_image(_make_ecg_12x1())
        assert result.accepted is True
        assert not any(i.severity == "error" for i in result.issues)

    def test_accepts_3x4_ecg(self):
        result = validate_ecg_image(_make_ecg_3x4())
        assert result.accepted is True
        assert not any(i.severity == "error" for i in result.issues)


class TestMetrics:
    """Metrics and issue structure validation."""

    def test_metrics_populated(self):
        result = validate_ecg_image(_make_ecg_12x1())
        assert isinstance(result, ValidationResult)
        assert isinstance(result.metrics, ValidationMetrics)
        m = result.metrics
        assert 0.0 <= m.dark_pixel_ratio <= 1.0
        assert m.content_band_count >= 0
        assert m.aspect_ratio > 0
        assert 0.0 <= m.foreground_rows_ratio <= 1.0
        assert 0.0 <= m.foreground_cols_ratio <= 1.0

    def test_issues_have_required_fields(self):
        result = validate_ecg_image(_make_blank_white())
        for issue in result.issues:
            assert isinstance(issue, PipelineIssue)
            assert isinstance(issue.code, str)
            assert isinstance(issue.message, str)
            assert issue.severity in ("info", "warning", "error")
