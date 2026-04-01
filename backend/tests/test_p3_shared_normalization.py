"""
Tests for P3: Shared normalization of ECG signals.

These tests verify that the ECG image converter uses shared (global) normalization
instead of per-lead min-max normalization. Shared normalization preserves inter-lead
amplitude differences, which are clinically meaningful (e.g., V1 has small amplitude
while V5 has large amplitude).

All tests in this file are expected to FAIL until the shared normalization
implementation is added to ECGImageToSignal.
"""

import cv2
import numpy as np
import pytest

from ml.ecg_image_converter import ECGImageToSignal


# ---------------------------------------------------------------------------
# Helpers — synthetic signals and images
# ---------------------------------------------------------------------------

def _make_synthetic_signals(
    num_leads: int = 12,
    signal_length: int = 1000,
    std_values: list[float] | None = None,
) -> np.ndarray:
    """
    Create synthetic signals with prescribed standard deviations.

    Each lead is a sine wave + noise with the given std. Baseline (median)
    is set to different offsets per lead to simulate real ECG data.

    Args:
        num_leads: Number of leads (rows).
        signal_length: Samples per lead.
        std_values: Desired std for each lead. Defaults to evenly spaced
                    values from 5 to 20 if not provided.

    Returns:
        signals array of shape (num_leads, signal_length), dtype float32.
    """
    if std_values is None:
        std_values = [5.0 + 15.0 * i / (num_leads - 1) for i in range(num_leads)]

    assert len(std_values) == num_leads
    signals = np.zeros((num_leads, signal_length), dtype=np.float32)

    rng = np.random.RandomState(42)
    for i in range(num_leads):
        t = np.linspace(0, 4 * np.pi, signal_length, dtype=np.float32)
        # Sine wave with amplitude proportional to desired std
        # sin ranges [-1, 1], so amplitude = desired_std gives approx desired std
        wave = std_values[i] * np.sin(t + i * 0.5)
        # Add small noise
        noise = rng.randn(signal_length).astype(np.float32) * (std_values[i] * 0.1)
        # Add a per-lead baseline offset (simulates y-position)
        baseline = float(i * 10)
        signals[i] = wave + noise + baseline

    return signals


def _make_ecg_image_with_varying_amplitudes(
    height: int = 1200,
    width: int = 1000,
    num_leads: int = 12,
    amplitudes: list[int] | None = None,
) -> np.ndarray:
    """
    Create a synthetic ECG image where each lead has a different amplitude.

    Each lead is drawn as a sine wave trace in its own horizontal strip.
    The amplitude of each trace is controlled by the `amplitudes` parameter.

    Args:
        height: Image height.
        width: Image width.
        num_leads: Number of leads.
        amplitudes: Pixel amplitude for each lead's trace.
                    Defaults to [5, 8, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55].

    Returns:
        RGB image [H, W, 3] with black traces on white background.
    """
    if amplitudes is None:
        amplitudes = [5, 8, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55]

    assert len(amplitudes) == num_leads

    image = np.full((height, width, 3), 255, dtype=np.uint8)
    strip_height = height // num_leads

    for i in range(num_leads):
        y_center = i * strip_height + strip_height // 2
        amp = amplitudes[i]
        # Draw sine wave trace
        points = []
        for x in range(width):
            y_offset = int(amp * np.sin(2 * np.pi * 3 * x / width))
            y_pos = y_center + y_offset
            y_pos = np.clip(y_pos, 0, height - 1)
            points.append((x, y_pos))
        # Draw thick line for the trace
        for j in range(len(points) - 1):
            cv2.line(image, points[j], points[j + 1], (0, 0, 0), 2)

    return image


# ---------------------------------------------------------------------------
# Test class 1: TestSharedNormalization
# ---------------------------------------------------------------------------

class TestSharedNormalization:
    """
    Tests for the shared normalization method.

    These tests call _normalize_shared() directly or test the behavior that
    shared normalization should exhibit. They will fail until the method
    is implemented.
    """

    def test_preserves_amplitude_ordering(self):
        """
        After shared normalization, the ordering of per-lead standard
        deviations should be preserved.

        Given 3 synthetic signals with std = [5, 10, 20], the normalized
        signals should maintain the same ordering: lead 2 > lead 1 > lead 0
        in terms of standard deviation.
        """
        converter = ECGImageToSignal(signal_length=1000, num_leads=3)
        std_values = [5.0, 10.0, 20.0]
        signals = _make_synthetic_signals(num_leads=3, std_values=std_values)

        # Compute per-lead baselines (medians)
        baselines = np.median(signals, axis=1, keepdims=True)

        # The converter should have _normalize_shared
        normalized = converter._normalize_shared(signals, baselines)

        # Compute post-normalization stds
        post_stds = [float(np.std(normalized[i])) for i in range(3)]

        # Ordering should be preserved: lead 2 > lead 1 > lead 0
        assert post_stds[2] > post_stds[1], (
            f"Lead 2 std ({post_stds[2]:.4f}) should be > lead 1 std ({post_stds[1]:.4f})"
        )
        assert post_stds[1] > post_stds[0], (
            f"Lead 1 std ({post_stds[1]:.4f}) should be > lead 0 std ({post_stds[0]:.4f})"
        )

    def test_shared_scale_factor(self):
        """
        All leads should be scaled by approximately the same factor.

        With shared normalization, the scale factor is derived from the global
        robust range, so the ratio of any two leads' effective scale factors
        should be within [0.9, 1.1].
        """
        converter = ECGImageToSignal(signal_length=1000, num_leads=5)
        std_values = [3.0, 7.0, 12.0, 18.0, 25.0]
        signals = _make_synthetic_signals(num_leads=5, std_values=std_values)

        baselines = np.median(signals, axis=1, keepdims=True)
        normalized = converter._normalize_shared(signals, baselines)

        # Effective scale factor for each lead: ratio of pre-norm range to
        # post-norm range. With shared scaling, these should be approximately
        # the same.
        pre_ranges = []
        post_ranges = []
        for i in range(5):
            pre = float(np.ptp(signals[i]))  # peak-to-peak
            post = float(np.ptp(normalized[i]))
            pre_ranges.append(pre)
            post_ranges.append(post)

        # Compute effective scale factors (pre / post)
        scale_factors = [pre_ranges[i] / max(post_ranges[i], 1e-8) for i in range(5)]

        # Ratios between any two scale factors should be near 1.0
        for i in range(5):
            for j in range(i + 1, 5):
                ratio = scale_factors[i] / max(scale_factors[j], 1e-8)
                assert 0.9 <= ratio <= 1.1, (
                    f"Scale factor ratio between lead {i} ({scale_factors[i]:.4f}) "
                    f"and lead {j} ({scale_factors[j]:.4f}) is {ratio:.4f}, "
                    f"expected within [0.9, 1.1]"
                )

    def test_output_centered_near_zero(self):
        """
        After shared normalization, per-lead medians should be near zero.

        The normalization subtracts per-lead median as baseline removal,
        so the resulting signals should be centered near zero (within 0.1).
        """
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        signals = _make_synthetic_signals(num_leads=12)

        baselines = np.median(signals, axis=1, keepdims=True)
        normalized = converter._normalize_shared(signals, baselines)

        for i in range(12):
            median_val = float(np.median(normalized[i]))
            assert abs(median_val) < 0.1, (
                f"Lead {i} median after normalization is {median_val:.4f}, "
                f"expected |median| < 0.1"
            )

    def test_robust_to_outliers(self):
        """
        A signal with one extreme spike should not compress all other values.

        With robust normalization using 1st-99th percentile clipping, a single
        extreme outlier should not dominate the scale factor. The non-outlier
        portion of the signal should still have meaningful dynamic range.
        """
        converter = ECGImageToSignal(signal_length=1000, num_leads=3)
        rng = np.random.RandomState(123)

        # Create normal signals
        signals = np.zeros((3, 1000), dtype=np.float32)
        for i in range(3):
            t = np.linspace(0, 4 * np.pi, 1000, dtype=np.float32)
            signals[i] = 10.0 * np.sin(t + i) + rng.randn(1000).astype(np.float32) * 0.5

        # Add one extreme outlier spike to lead 0
        signals[0, 500] = 10000.0  # Extreme spike

        baselines = np.median(signals, axis=1, keepdims=True)
        normalized = converter._normalize_shared(signals, baselines)

        # The non-outlier portion of lead 0 (excluding indices 495-505) should
        # have meaningful dynamic range — its std should not be crushed to near zero.
        mask = np.ones(1000, dtype=bool)
        mask[495:505] = False
        non_outlier_signal = normalized[0, mask]

        non_outlier_std = float(np.std(non_outlier_signal))
        assert non_outlier_std > 0.01, (
            f"Non-outlier portion has std={non_outlier_std:.6f}, "
            f"suggesting outlier compressed the whole signal"
        )


# ---------------------------------------------------------------------------
# Test class 2: TestInterLeadPreservation
# ---------------------------------------------------------------------------

class TestInterLeadPreservation:
    """
    Tests verifying that inter-lead amplitude relationships are preserved.

    Per-lead min-max normalization destroys inter-lead relationships because
    every lead gets stretched to the same [0, 1] range. Shared normalization
    should preserve these relationships.
    """

    def test_amplitude_ratio_preserved(self):
        """
        If lead 0 has half the amplitude of lead 1 in raw data, after
        normalization lead 0 should still have approximately half the
        amplitude of lead 1.
        """
        converter = ECGImageToSignal(signal_length=1000, num_leads=2)
        # Lead 0: std ~5, lead 1: std ~10
        signals = _make_synthetic_signals(num_leads=2, std_values=[5.0, 10.0])

        baselines = np.median(signals, axis=1, keepdims=True)
        normalized = converter._normalize_shared(signals, baselines)

        # Compute amplitude as std
        std_0 = float(np.std(normalized[0]))
        std_1 = float(np.std(normalized[1]))

        # The ratio should be approximately 0.5 (within 30% tolerance)
        ratio = std_0 / max(std_1, 1e-8)
        assert 0.35 < ratio < 0.65, (
            f"Amplitude ratio lead0/lead1 is {ratio:.4f}, "
            f"expected ~0.5 (raw ratio was 5/10 = 0.5). "
            f"std_0={std_0:.4f}, std_1={std_1:.4f}"
        )

    def test_not_per_lead_minmax(self):
        """
        Per-lead min-max normalization would make all leads have identical
        range [0, 1]. Verify this does NOT happen with shared normalization.

        At least 2 leads should have different post-normalization ranges
        (peak-to-peak), confirming that per-lead min-max is NOT being used.
        """
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)
        # Use different amplitudes so that per-lead min-max would make them identical
        amplitudes = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
        signals = _make_synthetic_signals(num_leads=12, std_values=[
            float(a) for a in amplitudes
        ])

        baselines = np.median(signals, axis=1, keepdims=True)
        normalized = converter._normalize_shared(signals, baselines)

        # Compute per-lead ranges
        ranges = [float(np.ptp(normalized[i])) for i in range(12)]

        # With per-lead min-max, all ranges would be exactly equal.
        # Check that at least 2 leads have noticeably different ranges.
        unique_ranges = set()
        for r in ranges:
            # Round to avoid floating-point noise
            unique_ranges.add(round(r, 3))

        assert len(unique_ranges) > 1, (
            f"All leads have identical post-norm range ({ranges[0]:.6f}), "
            f"suggesting per-lead min-max normalization is being used"
        )

        # Additionally, the ratio of max-range to min-range should be > 1.5
        # given that input amplitudes span 5 to 60 (12x ratio)
        max_range = max(ranges)
        min_range = min(ranges)
        range_ratio = max_range / max(min_range, 1e-8)

        assert range_ratio > 1.5, (
            f"Range ratio (max/min) is {range_ratio:.2f}, expected > 1.5. "
            f"max_range={max_range:.4f}, min_range={min_range:.4f}"
        )


# ---------------------------------------------------------------------------
# Test class 3: TestIntegrationWithPipeline
# ---------------------------------------------------------------------------

class TestIntegrationWithPipeline:
    """
    Integration test: extract_with_result should use shared normalization.

    When extracting signals from a synthetic ECG image with varying lead
    amplitudes, the post-extraction signals should preserve those amplitude
    differences.
    """

    def test_extract_with_result_uses_shared_norm(self):
        """
        Extract signals from a synthetic ECG image where each lead has a
        different amplitude. After extraction, at least 3 leads should have
        noticeably different amplitudes (ratio of max-std to min-std > 1.5).

        This test will fail with the current per-lead min-max normalization
        because all leads get mapped to the same [0, 1] range, making their
        standard deviations approximately equal.
        """
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)

        # Create image with widely varying amplitudes
        amplitudes = [3, 6, 10, 15, 20, 25, 30, 36, 42, 48, 55, 60]
        image = _make_ecg_image_with_varying_amplitudes(
            height=1200, width=1000, num_leads=12, amplitudes=amplitudes,
        )

        result = converter.extract_with_result(image)
        assert result.signals.shape == (12, 1000)

        # Compute per-lead std
        stds = [float(np.std(result.signals[i])) for i in range(12)]
        max_std = max(stds)
        min_std = min(stds)

        std_ratio = max_std / max(min_std, 1e-8)

        assert std_ratio > 1.5, (
            f"Post-extraction std ratio (max/min) is {std_ratio:.2f}, "
            f"expected > 1.5. This suggests per-lead normalization is being "
            f"used instead of shared normalization. "
            f"stds={[f'{s:.4f}' for s in stds]}"
        )

    def test_extract_preserves_amplitude_ordering(self):
        """
        After full extraction pipeline, leads drawn with larger amplitudes
        in the image should have larger standard deviations in the output.

        This is a weaker version of the above — just checks that ordering
        is roughly preserved, not the exact ratio.
        """
        converter = ECGImageToSignal(signal_length=1000, num_leads=12)

        amplitudes = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
        image = _make_ecg_image_with_varying_amplitudes(
            height=1200, width=1000, num_leads=12, amplitudes=amplitudes,
        )

        result = converter.extract_with_result(image)

        stds = [float(np.std(result.signals[i])) for i in range(12)]

        # Lead 11 (amplitude=60) should have larger std than lead 0 (amplitude=5)
        assert stds[11] > stds[0], (
            f"Lead 11 std ({stds[11]:.4f}) should be > lead 0 std ({stds[0]:.4f}), "
            f"because lead 11 was drawn with 12x larger amplitude"
        )
