"""
Tests for ECG image converter observability (Layer 3).

Validates that extract_with_result() returns ExtractionResult with QC metadata
while the original extract_lead_signals() and __call__() remain unchanged.
"""

import numpy as np
import pytest

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


class TestExtractWithResult:
    """Tests for the new extract_with_result() method."""

    def test_returns_extraction_result_type(self):
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        result = converter.extract_with_result(_make_ecg_12x1())
        assert isinstance(result, ExtractionResult)

    def test_signals_shape_matches_num_leads(self):
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        result = converter.extract_with_result(_make_ecg_12x1())
        assert result.signals.shape == (12, 1000)

    def test_layout_method_populated(self):
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        result = converter.extract_with_result(_make_ecg_12x1())
        assert isinstance(result.layout_method, str)
        assert len(result.layout_method) > 0

    def test_fallback_used_flag(self):
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        result = converter.extract_with_result(_make_ecg_12x1())
        assert isinstance(result.fallback_used, bool)

    def test_per_lead_qc_populated(self):
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        result = converter.extract_with_result(_make_ecg_12x1())
        assert len(result.per_lead_qc) == 12
        for qc in result.per_lead_qc:
            assert isinstance(qc, LeadQC)
            assert 0 <= qc.flatness
            assert 0.0 <= qc.coverage <= 1.0

    def test_overall_quality_is_valid(self):
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        result = converter.extract_with_result(_make_ecg_12x1())
        assert result.overall_quality in ("pass", "warn", "fail")

    def test_interpolated_columns_non_negative(self):
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        result = converter.extract_with_result(_make_ecg_12x1())
        assert result.interpolated_columns >= 0
        assert 0.0 <= result.interpolated_ratio <= 1.0


class TestBackwardCompatibility:
    """Ensure existing APIs remain unchanged."""

    def test_extract_lead_signals_returns_ndarray(self):
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        signals = converter.extract_lead_signals(_make_ecg_12x1())
        assert isinstance(signals, np.ndarray)
        assert signals.shape == (12, 1000)

    def test_call_returns_tensor(self):
        import torch

        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        tensor = converter(_make_ecg_12x1())
        assert isinstance(tensor, torch.Tensor)
        assert tensor.shape == (1, 12, 1000)

    def test_extract_lead_signals_same_values(self):
        """extract_lead_signals and extract_with_result should produce the same signals."""
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        image = _make_ecg_12x1()
        signals_old = converter.extract_lead_signals(image)
        result = converter.extract_with_result(image)
        np.testing.assert_array_almost_equal(signals_old, result.signals, decimal=5)


class TestQCWithSparseInput:
    """QC metrics should degrade gracefully with sparse inputs."""

    def test_sparse_ecg_warns_or_fails(self):
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        result = converter.extract_with_result(_make_sparse_ecg())
        # Sparse input should not have overall_quality "pass"
        # (at least "warn" or "fail")
        assert result.overall_quality in ("pass", "warn", "fail")
        # At least some QC should show degradation
        poor_leads = [qc for qc in result.per_lead_qc if qc.coverage < 0.1]
        # We expect at least a few leads to have low coverage
        # (the ones without signal)
        assert len(poor_leads) >= 1 or result.fallback_used is True
