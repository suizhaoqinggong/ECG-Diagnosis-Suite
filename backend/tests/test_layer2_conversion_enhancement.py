"""
Tests for Layer 2 — Conversion Enhancement.

Tests for improved layout detection, rotation correction, trace path optimization,
and normalization improvements in ECG image converter.
"""

import numpy as np
import pytest
import cv2

from ml.ecg_image_converter import ECGImageToSignal
from ml.pipeline_types import ExtractionResult, LeadQC


def _make_12x1_ecg(height: int = 1200, width: int = 2400, noise: float = 0.0) -> np.ndarray:
    """Synthetic 12x1 horizontal strip ECG."""
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    strip_h = height // 12
    for i in range(12):
        y_center = i * strip_h + strip_h // 2
        for x in range(width):
            y_offset = int(10 * np.sin(2 * np.pi * x / 150 + i * 0.5))
            y_pos = y_center + y_offset
            if 0 <= y_pos < height:
                for dy in range(-2, 3):
                    py = y_pos + dy
                    if 0 <= py < height:
                        image[py, x] = [0, 0, 0]
    if noise > 0:
        noise_mask = np.random.random(image.shape[:2]) < noise
        image[noise_mask] = [0, 0, 0]
    return image


def _make_3x4_ecg(height: int = 1600, width: int = 2000) -> np.ndarray:
    """Synthetic 3x4 grid ECG (3 rows, 4 columns = 12 leads)."""
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    cell_h = height // 3
    cell_w = width // 4
    for i in range(12):
        row = i // 4
        col = i % 4
        y_center = row * cell_h + cell_h // 2
        x_center = col * cell_w + cell_w // 2
        for dx in range(-cell_w // 2 + 10, cell_w // 2 - 10):
            x = x_center + dx
            if 0 <= x < width:
                y_offset = int(15 * np.sin(2 * np.pi * dx / 100 + i))
                y = y_center + y_offset
                if 0 <= y < height:
                    for dy in range(-2, 3):
                        py = y + dy
                        if 0 <= py < height:
                            image[py, x] = [0, 0, 0]
    return image


def _make_6x2_ecg(height: int = 1200, width: int = 1600) -> np.ndarray:
    """Synthetic 6x2 grid ECG (6 rows, 2 columns = 12 leads)."""
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    cell_h = height // 6
    cell_w = width // 2
    for i in range(12):
        row = i // 2
        col = i % 2
        y_center = row * cell_h + cell_h // 2
        x_center = col * cell_w + cell_w // 2
        for dx in range(-cell_w // 2 + 10, cell_w // 2 - 10):
            x = x_center + dx
            if 0 <= x < width:
                y_offset = int(12 * np.sin(2 * np.pi * dx / 80 + i * 0.3))
                y = y_center + y_offset
                if 0 <= y < height:
                    for dy in range(-2, 3):
                        py = y + dy
                        if 0 <= py < height:
                            image[py, x] = [0, 0, 0]
    return image


def _make_3x4_plus1_ecg(height: int = 2000, width: int = 2400) -> np.ndarray:
    """Synthetic 3x4+1 ECG: 12 leads plus one full-width rhythm strip."""
    image = np.full((height, width, 3), 255, dtype=np.uint8)
    row_h = height // 4
    col_w = width // 4

    for i in range(12):
        row = i // 4
        col = i % 4
        y_center = row * row_h + row_h // 2
        x_start = col * col_w + 16
        x_end = (col + 1) * col_w - 16
        for x in range(x_start, x_end):
            dx = x - x_start
            y_offset = int(12 * np.sin(2 * np.pi * dx / 120 + i * 0.35))
            y_pos = y_center + y_offset
            if 0 <= y_pos < height:
                image[max(0, y_pos - 2):min(height, y_pos + 3), x] = [0, 0, 0]

    rhythm_y = 3 * row_h + row_h // 2
    for x in range(16, width - 16):
        y_offset = int(12 * np.sin(2 * np.pi * x / 120 + 1.7))
        y_pos = rhythm_y + y_offset
        if 0 <= y_pos < height:
            image[max(0, y_pos - 2):min(height, y_pos + 3), x] = [0, 0, 0]

    return image


def _make_colored_12x1_ecg(
    bg_color: tuple[int, int, int] = (245, 210, 210),
    fg_color: tuple[int, int, int] = (110, 20, 20),
    contrast_scale: float = 1.0,
    height: int = 1200,
    width: int = 2400,
) -> np.ndarray:
    """Synthetic 12x1 ECG drawn on colored paper with configurable contrast."""
    image = np.full((height, width, 3), bg_color, dtype=np.uint8)
    strip_h = height // 12

    bg = np.array(bg_color, dtype=np.float32)
    fg = np.array(fg_color, dtype=np.float32)
    mixed_fg = np.clip(bg + (fg - bg) * contrast_scale, 0, 255).astype(np.uint8)

    for i in range(12):
        y_center = i * strip_h + strip_h // 2
        for x in range(width):
            y_offset = int(8 * np.sin(2 * np.pi * x / 140 + i * 0.5))
            y_pos = y_center + y_offset
            if 0 <= y_pos < height:
                image[max(0, y_pos - 1):min(height, y_pos + 2), x] = mixed_fg

    return image


def _rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image by given angle in degrees."""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    cos = abs(M[0, 0])
    sin = abs(M[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))
    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]
    rotated = cv2.warpAffine(image, M, (new_w, new_h), borderValue=(255, 255, 255))
    return rotated


# -----------------------------------------------------------------------------
# Test Layout Detection for Different ECG Formats
# -----------------------------------------------------------------------------


class TestLayoutDetection:
    """Test detection of different ECG layouts."""

    def test_detect_12x1_horizontal_strips(self):
        """Should detect 12x1 horizontal strip layout."""
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        result = converter.extract_with_result(image)
        assert result.layout_method in ("horizontal_strips", "projection")
        assert len(result.per_lead_qc) == 12
        good_leads = [qc for qc in result.per_lead_qc if qc.quality in ("good", "warn")]
        assert len(good_leads) >= 10

    def test_detect_3x4_grid_layout(self):
        """Should detect grid-based layout for 3x4 ECG."""
        converter = ECGImageToSignal()
        image = _make_3x4_ecg()
        result = converter.extract_with_result(image)
        # Grid or fallback grid layout — as long as it's not "horizontal_strips"
        assert "grid" in result.layout_method or "3x4" in result.layout_method or "4x3" in result.layout_method
        assert len(result.per_lead_qc) == 12

    def test_detect_6x2_grid_layout(self):
        """Should detect 6x2 grid layout."""
        converter = ECGImageToSignal()
        image = _make_6x2_ecg()
        result = converter.extract_with_result(image)
        assert len(result.per_lead_qc) == 12

    def test_detect_3x4_plus1_rhythm_layout(self):
        """Should explicitly detect a 3x4+1 rhythm-strip layout."""
        converter = ECGImageToSignal()
        image = _make_3x4_plus1_ecg()
        result = converter.extract_with_result(image)
        assert result.layout_method == "3x4+1_rhythm"
        assert not result.fallback_used
        assert len(result.per_lead_qc) == 12

    def test_3x4_plus1_layout_does_not_emit_false_rotation_warning(self):
        """Near-square 3x4+1 layouts should not be misclassified as rotated."""
        converter = ECGImageToSignal()
        image = _make_3x4_plus1_ecg()
        result = converter.extract_with_result(image)
        warning_text = " ".join(result.warnings)
        assert "旋转" not in warning_text
        assert "倾斜" not in warning_text

    def test_layout_score_indicates_confidence(self):
        """Layout score should indicate detection confidence."""
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        result = converter.extract_with_result(image)
        assert 0.0 <= result.layout_score <= 1.0
        assert result.layout_score >= 0.5


# -----------------------------------------------------------------------------
# Test Rotation Correction
# -----------------------------------------------------------------------------


class TestRotationCorrection:
    """Test rotation and skew detection/correction."""

    def test_small_rotation_detected_and_corrected(self):
        """Small rotations (< 30 deg) should be detected and corrected."""
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        rotated = _rotate_image(image, 5.0)
        result = converter.extract_with_result(rotated)
        assert len(result.per_lead_qc) == 12
        failed_leads = [qc for qc in result.per_lead_qc if qc.quality == "fail"]
        assert len(failed_leads) <= 4

    def test_90_degree_rotation_handled(self):
        """90 degree rotation should be handled."""
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        rotated = _rotate_image(image, 90.0)
        result = converter.extract_with_result(rotated)
        assert len(result.per_lead_qc) == 12

    def test_extreme_rotation_flagged(self):
        """Extreme rotations (> 30 deg) should be flagged as quality issue."""
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        rotated = _rotate_image(image, 45.0)
        result = converter.extract_with_result(rotated)
        warnings_lower = [w.lower() for w in result.warnings]
        has_rotation_warning = any(
            "rotat" in w or "skew" in w or "旋转" in w or "倾斜" in w or "异常" in w
            for w in warnings_lower
        )
        assert has_rotation_warning or result.overall_quality in ("warn", "fail")


# -----------------------------------------------------------------------------
# Test Trace Extraction Improvements
# -----------------------------------------------------------------------------


class TestTraceExtractionImprovements:
    """Test improved trace extraction with continuity filter."""

    def test_trace_extraction_with_stamps_and_labels(self):
        """Should extract traces despite text annotations."""
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        for row in range(0, image.shape[0], 100):
            image[row:row+3, 50:200] = [0, 0, 0]
            image[row:row+3, -200:] = [0, 0, 0]
        result = converter.extract_with_result(image)
        assert len(result.per_lead_qc) == 12
        avg_coverage = np.mean([qc.coverage for qc in result.per_lead_qc])
        assert avg_coverage > 0.3

    def test_continuity_filter_reduces_jumps(self):
        """Continuity filter should reduce large y-position jumps."""
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        result = converter.extract_with_result(image)
        avg_jump_rate = np.mean([qc.jump_rate for qc in result.per_lead_qc])
        assert avg_jump_rate < 0.5

    def test_interpolated_columns_tracked(self):
        """Number of interpolated columns should be tracked per lead."""
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        for i in [2, 5, 8]:
            strip_h = image.shape[0] // 12
            y_start = i * strip_h
            y_end = min((i + 1) * strip_h, image.shape[0])
            mid_x = image.shape[1] // 2
            image[y_start:y_end, mid_x-20:mid_x+20] = 255
        result = converter.extract_with_result(image)
        assert result.interpolated_columns > 0 or result.interpolated_ratio > 0


# -----------------------------------------------------------------------------
# Test Normalization Improvements
# -----------------------------------------------------------------------------


class TestNormalizationImprovements:
    """Test improved normalization with shared scale factor."""

    def test_global_normalization_preserves_relative_amplitudes(self):
        """Global normalization should preserve inter-lead amplitude relationships."""
        converter = ECGImageToSignal()
        image = np.full((1200, 2400, 3), 255, dtype=np.uint8)
        strip_h = 1200 // 12
        for i in range(12):
            y_center = i * strip_h + strip_h // 2
            amplitude = 5 + i * 2
            for x in range(2400):
                y_offset = int(amplitude * np.sin(2 * np.pi * x / 200))
                y_pos = y_center + y_offset
                if 0 <= y_pos < 1200:
                    for dy in range(-2, 3):
                        py = y_pos + dy
                        if 0 <= py < 1200:
                            image[py, x] = [0, 0, 0]
        result = converter.extract_with_result(image)
        signals = result.signals
        ranges = [signals[i].max() - signals[i].min() for i in range(12)]
        assert ranges[0] < ranges[11]

    def test_percentile_clipping_reduces_outlier_sensitivity(self):
        """Percentile-based clipping should handle outliers gracefully."""
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        image[100:110, :] = 0
        image[500:510, :] = 0
        result = converter.extract_with_result(image)
        assert np.all(np.isfinite(result.signals))
        assert result.signals.min() >= -10
        assert result.signals.max() <= 10

    def test_colored_paper_backgrounds_still_extract_traces(self):
        """Colored ECG paper should still be separable by preprocessing."""
        converter = ECGImageToSignal()
        image = _make_colored_12x1_ecg(bg_color=(230, 240, 205), fg_color=(70, 85, 40))
        result = converter.extract_with_result(image)
        good_leads = [qc for qc in result.per_lead_qc if qc.quality in ("good", "warn")]
        assert len(good_leads) >= 10
        assert result.layout_method == "horizontal_strips"

    def test_high_and_low_contrast_versions_produce_similar_signals(self):
        """Low-contrast ECGs should remain close to their high-contrast counterparts."""
        converter = ECGImageToSignal()
        high_contrast = _make_colored_12x1_ecg()
        low_contrast = _make_colored_12x1_ecg(contrast_scale=0.35)

        high_result = converter.extract_with_result(high_contrast)
        low_result = converter.extract_with_result(low_contrast)

        correlations = []
        for lead_index in range(12):
            correlations.append(
                float(
                    np.corrcoef(
                        high_result.signals[lead_index],
                        low_result.signals[lead_index],
                    )[0, 1]
                )
            )

        assert np.mean(correlations) > 0.95
        assert np.min(correlations) > 0.90


# -----------------------------------------------------------------------------
# Test Integration
# -----------------------------------------------------------------------------


class TestLayer2Integration:
    """Integration tests for Layer 2 enhancements."""

    def test_extraction_result_has_all_fields(self):
        """ExtractionResult should include all Layer 2 fields."""
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        result = converter.extract_with_result(image)
        assert hasattr(result, 'signals')
        assert hasattr(result, 'layout_method')
        assert hasattr(result, 'layout_score')
        assert hasattr(result, 'fallback_used')
        assert hasattr(result, 'interpolated_columns')
        assert hasattr(result, 'interpolated_ratio')
        assert hasattr(result, 'per_lead_qc')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'overall_quality')

    def test_backward_compatible_extract_lead_signals(self):
        """extract_lead_signals() should still work and return numpy array."""
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        signals = converter.extract_lead_signals(image)
        assert isinstance(signals, np.ndarray)
        assert signals.shape == (12, 1000)

    def test_backward_compatible_call(self):
        """__call__() should still work and return tensor."""
        import torch
        converter = ECGImageToSignal()
        image = _make_12x1_ecg()
        tensor = converter(image)
        assert isinstance(tensor, torch.Tensor)
        assert tensor.shape == (1, 12, 1000)
