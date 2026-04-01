"""
Tests for P2: Continuity-constrained vertical centroid extraction.

These tests verify the new _extract_trace_centroid method that will replace
the current np.mean(strip, axis=0) approach. The method should:

1. For each column in a binary strip, find vertical runs of dark pixels
2. Filter runs: reject tiny (< 2px) and overly tall (> 40% of strip height)
3. For each valid run, compute its center Y position
4. Select the run center closest to the previous column's selected center
5. Mark gaps (no valid run) as NaN, then interpolate from neighbors
6. Invert signal: upward deflection = positive (y increases downward in images)
7. Light Savitzky-Golay smoothing

ALL TESTS WILL FAIL because _extract_trace_centroid does not exist yet.
"""

import cv2
import numpy as np
import pytest

from ml.ecg_image_converter import ECGImageToSignal


# ---------------------------------------------------------------------------
# Helpers — synthetic binary strips and ECG images
# ---------------------------------------------------------------------------

def _white_strip(height: int = 100, width: int = 200) -> np.ndarray:
    """Create an all-white (0) binary strip: no dark pixels."""
    return np.zeros((height, width), dtype=np.uint8)


def _horizontal_line_strip(
    row: int = 30,
    height: int = 100,
    width: int = 200,
    thickness: int = 2,
) -> np.ndarray:
    """Create a binary strip with a dark horizontal line at the given row."""
    strip = np.zeros((height, width), dtype=np.uint8)
    y_start = max(row - thickness // 2, 0)
    y_end = min(row + thickness // 2 + 1, height)
    strip[y_start:y_end, :] = 255
    return strip


def _sine_wave_strip(
    height: int = 100,
    width: int = 200,
    y_center: int = 50,
    amplitude: int = 20,
    frequency: float = 3.0,
    thickness: int = 2,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Draw a sine-wave trace in a binary strip.

    Returns:
        (strip, y_positions) where y_positions[x] is the center Y of the trace
        at column x.
    """
    strip = np.zeros((height, width), dtype=np.uint8)
    y_positions = np.zeros(width, dtype=np.float64)

    for x in range(width):
        y = int(y_center + amplitude * np.sin(2 * np.pi * frequency * x / width))
        y = np.clip(y, 0, height - 1)
        y_positions[x] = y
        y_lo = max(y - thickness // 2, 0)
        y_hi = min(y + thickness // 2 + 1, height)
        strip[y_lo:y_hi, x] = 255

    return strip, y_positions


def _strip_with_gap(
    height: int = 100,
    width: int = 200,
    row: int = 50,
    gap_start: int = 90,
    gap_end: int = 110,
    thickness: int = 2,
) -> np.ndarray:
    """Create a binary strip with a horizontal line that has a gap in the middle."""
    strip = np.zeros((height, width), dtype=np.uint8)
    y_start = max(row - thickness // 2, 0)
    y_end = min(row + thickness // 2 + 1, height)

    # Draw line everywhere except the gap
    strip[y_start:y_end, :gap_start] = 255
    strip[y_start:y_end, gap_end:] = 255
    return strip


def _strip_with_noise_pixel(
    height: int = 100,
    width: int = 200,
    trace_row: int = 50,
    noise_row: int = 20,
    noise_col: int = 100,
    thickness: int = 2,
) -> np.ndarray:
    """
    Create a strip with a horizontal line trace and a single-pixel noise artifact
    at (noise_row, noise_col).
    """
    strip = _horizontal_line_strip(row=trace_row, height=height, width=width, thickness=thickness)
    strip[noise_row, noise_col] = 255
    return strip


def _strip_with_full_column_dark(
    height: int = 100,
    width: int = 200,
    trace_row: int = 50,
    dark_col: int = 100,
    thickness: int = 2,
) -> np.ndarray:
    """
    Create a strip with a horizontal line trace and a full-height dark column
    (simulating a label or artifact).
    """
    strip = _horizontal_line_strip(row=trace_row, height=height, width=width, thickness=thickness)
    strip[:, dark_col] = 255  # Entire column is dark
    return strip


def _strip_with_two_runs(
    height: int = 100,
    width: int = 200,
    trace_row: int = 50,
    artifact_row: int = 20,
    artifact_col: int = 100,
    artifact_width: int = 3,
    thickness: int = 2,
) -> np.ndarray:
    """
    Create a strip with a horizontal line trace and a small artifact at a
    specific column, producing two distinct runs in that column.
    """
    strip = _horizontal_line_strip(row=trace_row, height=height, width=width, thickness=thickness)
    # Add a short horizontal artifact near artifact_row
    col_start = max(artifact_col - artifact_width // 2, 0)
    col_end = min(artifact_col + artifact_width // 2 + 1, width)
    y_lo = max(artifact_row - 1, 0)
    y_hi = min(artifact_row + 2, height)
    strip[y_lo:y_hi, col_start:col_end] = 255
    return strip


def _make_synthetic_ecg_image_with_distinct_leads(
    height: int = 1200,
    width: int = 1000,
    num_leads: int = 12,
) -> tuple[np.ndarray, list[float]]:
    """
    Create a synthetic ECG image where each lead has a DIFFERENT sine frequency.

    Returns:
        (image, frequencies) — the image and the list of frequencies per lead.
    """
    img = np.full((height, width, 3), 255, dtype=np.uint8)
    strip_height = height // num_leads
    frequencies = []

    for i in range(num_leads):
        freq = 1.0 + i * 0.8  # Each lead gets a distinct frequency
        frequencies.append(freq)
        y_center = int((i + 0.5) * strip_height)
        amplitude = min(strip_height * 0.3, 25)

        for x in range(width):
            y = int(y_center + amplitude * np.sin(2 * np.pi * freq * x / width))
            y = np.clip(y, 0, height - 1)
            # Draw a 2px thick trace
            for dy in range(-1, 2):
                yy = y + dy
                if 0 <= yy < height:
                    img[yy, x] = (0, 0, 0)

    return img, frequencies


def _make_upward_deflection_strip(
    height: int = 100,
    width: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Create a strip where the trace goes UP (lower y values) in the middle,
    then comes back down.

    Returns:
        (strip, y_positions) — the binary strip and the true Y positions.
    """
    strip = np.zeros((height, width), dtype=np.uint8)
    y_positions = np.zeros(width, dtype=np.float64)

    for x in range(width):
        # V-shape: start at row 70, go up to row 30 in the middle, back to 70
        y = 70 - 40 * np.sin(np.pi * x / width)
        y = int(np.clip(y, 0, height - 1))
        y_positions[x] = y
        y_lo = max(y - 1, 0)
        y_hi = min(y + 2, height)
        strip[y_lo:y_hi, x] = 255

    return strip, y_positions


# ---------------------------------------------------------------------------
# Test class 1: TestCentroidExtractionBasic
# ---------------------------------------------------------------------------

class TestCentroidExtractionBasic:
    """Basic tests for _extract_trace_centroid."""

    def test_returns_1d_array(self):
        """_extract_trace_centroid(strip) should return a 1-D array of length = strip width."""
        converter = ECGImageToSignal()
        strip = _horizontal_line_strip(row=30, height=100, width=200)

        result = converter._extract_trace_centroid(strip)

        assert isinstance(result, np.ndarray), (
            f"Expected np.ndarray, got {type(result)}"
        )
        assert result.ndim == 1, f"Expected 1-D array, got {result.ndim}-D"
        assert len(result) == 200, (
            f"Expected length 200 (strip width), got {len(result)}"
        )

    def test_single_horizontal_line(self):
        """A thin dark line at row 30 in a 100-row strip should give signal near 30."""
        converter = ECGImageToSignal()
        row = 30
        strip = _horizontal_line_strip(row=row, height=100, width=200)

        signal = converter._extract_trace_centroid(strip)

        # After inversion (y increases downward, so invert),
        # the signal value should correspond to row 30.
        # If the method inverts: signal_value = height - y,
        # then we expect signal ~= 100 - 30 = 70.
        # If it simply returns the y position (no inversion),
        # then we expect ~= 30.
        # We accept either convention as long as it's consistent.
        # The key is: the signal should NOT be near 0 or near 100 (random),
        # it should clearly correspond to the trace position.
        mean_signal = float(np.nanmean(signal))
        # The mean signal (after whatever transform) should not be near the
        # strip edges — it should reflect the trace at row 30.
        # Check that the signal is roughly constant (flat line) with low std
        # (the trace is a straight horizontal line).
        std_signal = float(np.nanstd(signal))
        assert std_signal < 10.0, (
            f"A horizontal line should produce a nearly flat signal, "
            f"got std={std_signal:.2f}"
        )
        # The signal values should be distinguishable from random noise.
        # Specifically, most values should be within a narrow band.
        assert not np.all(np.isnan(signal)), "Signal should not be all NaN"

    def test_sine_wave_trace(self):
        """A sine-wave trace should produce a signal that correlates > 0.8 with true Y positions."""
        converter = ECGImageToSignal()
        strip, true_y = _sine_wave_strip(
            height=100, width=200, y_center=50, amplitude=20, frequency=3.0,
        )

        signal = converter._extract_trace_centroid(strip)

        assert not np.any(np.isnan(signal)), (
            "Signal should have no NaN for a continuous sine-wave trace"
        )

        # The signal should be monotonic with true_y (possibly inverted).
        # Check both positive and negative correlation.
        corr_pos = np.corrcoef(signal, true_y)[0, 1]
        corr_neg = np.corrcoef(signal, -true_y)[0, 1]
        best_corr = max(abs(corr_pos), abs(corr_neg))

        assert best_corr > 0.8, (
            f"Signal should correlate > 0.8 with true Y positions, "
            f"got best correlation = {best_corr:.3f}"
        )

    def test_gap_interpolation(self):
        """A trace with a 20-column gap should be smoothly interpolated, not zero or NaN."""
        converter = ECGImageToSignal()
        gap_start, gap_end = 90, 110
        strip = _strip_with_gap(
            height=100, width=200, row=50,
            gap_start=gap_start, gap_end=gap_end,
        )

        signal = converter._extract_trace_centroid(strip)

        # Signal should have no NaN in the gap region
        gap_signal = signal[gap_start:gap_end]
        assert not np.any(np.isnan(gap_signal)), (
            "Gap region should be interpolated (no NaN)"
        )

        # The gap signal should not be all zeros
        assert not np.all(gap_signal == 0), (
            "Gap region should not be all zeros — it should be interpolated"
        )

        # The interpolated values should be roughly similar to neighboring values
        # Check that gap values are within a reasonable range of the trace level
        left_val = float(signal[gap_start - 1])
        right_val = float(signal[gap_end])
        gap_mean = float(np.mean(gap_signal))
        neighbor_mean = (left_val + right_val) / 2.0

        # The interpolation should be smooth: gap mean close to neighbor mean
        # Allow generous tolerance since the method may apply smoothing
        assert abs(gap_mean - neighbor_mean) < 30.0, (
            f"Interpolated gap mean ({gap_mean:.1f}) too far from "
            f"neighbor mean ({neighbor_mean:.1f})"
        )

    def test_empty_strip(self):
        """An all-white strip (no dark pixels) should be handled gracefully — not all NaN."""
        converter = ECGImageToSignal()
        strip = _white_strip(height=100, width=200)

        signal = converter._extract_trace_centroid(strip)

        # The signal should still be a 1-D array of the correct length
        assert signal.ndim == 1
        assert len(signal) == 200

        # The signal should be usable — either all interpolated (no NaN)
        # or have at most a small fraction of NaN
        nan_fraction = float(np.mean(np.isnan(signal)))
        assert nan_fraction < 0.5, (
            f"Empty strip should not produce > 50% NaN, got {nan_fraction:.0%}"
        )


# ---------------------------------------------------------------------------
# Test class 2: TestRunFiltering
# ---------------------------------------------------------------------------

class TestRunFiltering:
    """Tests for the run filtering logic within _extract_trace_centroid."""

    def test_rejects_tiny_runs(self):
        """Isolated single-pixel noise should be ignored by the extraction."""
        converter = ECGImageToSignal()
        trace_row = 50
        noise_row = 20
        noise_col = 100
        strip = _strip_with_noise_pixel(
            height=100, width=200,
            trace_row=trace_row, noise_row=noise_row, noise_col=noise_col,
        )

        signal = converter._extract_trace_centroid(strip)

        # The signal at the noise column should still follow the trace at row 50,
        # not jump to row 20 where the noise is.
        # Check that the signal at noise_col is similar to its neighbors
        neighbor_val = float(signal[noise_col - 1])
        noise_col_val = float(signal[noise_col])
        next_val = float(signal[noise_col + 1])

        # The noise should not cause a large jump
        jump_before = abs(noise_col_val - neighbor_val)
        assert jump_before < 15.0, (
            f"Single-pixel noise at col {noise_col} caused a jump of "
            f"{jump_before:.1f} (should be < 15)"
        )

    def test_rejects_tall_runs(self):
        """A full-column dark region (like a label) should be rejected."""
        converter = ECGImageToSignal()
        trace_row = 50
        dark_col = 100
        strip = _strip_with_full_column_dark(
            height=100, width=200,
            trace_row=trace_row, dark_col=dark_col,
        )

        signal = converter._extract_trace_centroid(strip)

        # At dark_col, the signal should follow the trace, not jump to some
        # average of the full-column dark region.
        # The signal should be smooth across dark_col
        left_val = float(signal[dark_col - 1])
        dark_col_val = float(signal[dark_col])
        right_val = float(signal[dark_col + 1])

        # The full-column artifact should not cause a large deviation
        neighbor_avg = (left_val + right_val) / 2.0
        deviation = abs(dark_col_val - neighbor_avg)
        assert deviation < 20.0, (
            f"Full-column dark at col {dark_col} caused deviation of "
            f"{deviation:.1f} from neighbors (should be < 20)"
        )

    def test_selects_continuity(self):
        """When two runs exist, the one closest to the previous center should win."""
        converter = ECGImageToSignal()
        trace_row = 50
        artifact_row = 20
        artifact_col = 100
        strip = _strip_with_two_runs(
            height=100, width=200,
            trace_row=trace_row, artifact_row=artifact_row,
            artifact_col=artifact_col, artifact_width=3,
        )

        signal = converter._extract_trace_centroid(strip)

        # The artifact is at row 20, far from the trace at row 50.
        # The continuity constraint should select the run at row 50.
        # Check that the signal around artifact_col tracks the trace, not the artifact.
        left_val = float(signal[artifact_col - 1])
        center_val = float(signal[artifact_col])
        right_val = float(signal[artifact_col + 1])

        # If continuity works, the signal should be smooth (following the row 50 trace)
        # and NOT jump toward row 20.
        max_jump = max(abs(center_val - left_val), abs(center_val - right_val))
        assert max_jump < 15.0, (
            f"Two-run column at col {artifact_col} caused a jump of {max_jump:.1f} "
            f"— continuity should prefer the closer run at row {trace_row}"
        )


# ---------------------------------------------------------------------------
# Test class 3: TestSignalInversion
# ---------------------------------------------------------------------------

class TestSignalInversion:
    """Tests for the signal inversion (upward deflection = positive)."""

    def test_upward_deflection_positive(self):
        """
        A trace that goes UP in the image (lower y values) should produce
        positive signal values at that point.
        """
        converter = ECGImageToSignal()
        strip, true_y = _make_upward_deflection_strip(height=100, width=200)

        signal = converter._extract_trace_centroid(strip)

        assert not np.any(np.isnan(signal)), "Signal should have no NaN"

        # The trace goes UP (y decreases) in the middle of the strip.
        # After inversion, upward deflection should be positive.
        # So the signal should have its MAXIMUM near the middle (where y is smallest).
        mid_col = 100  # Middle column
        edge_col = 10  # Edge, where the trace is at row ~70

        # The signal at the middle should be HIGHER than at the edge
        # because the trace goes up (lower y) -> positive deflection after inversion.
        mid_val = float(signal[mid_col])
        edge_val = float(signal[edge_col])

        assert mid_val > edge_val, (
            f"Upward deflection should be positive: mid_val ({mid_val:.2f}) "
            f"should be > edge_val ({edge_val:.2f})"
        )


# ---------------------------------------------------------------------------
# Test class 4: TestIntegrationWithPipeline
# ---------------------------------------------------------------------------

class TestIntegrationWithPipeline:
    """Integration tests: _extract_trace_centroid used via extract_with_result."""

    def test_extract_with_result_uses_centroid(self):
        """
        extract_with_result on a synthetic ECG image with different waveforms
        per lead should produce signals where at least 8 of 12 leads are 'good'.
        """
        converter = ECGImageToSignal()
        img, _ = _make_synthetic_ecg_image_with_distinct_leads(
            height=1200, width=1000, num_leads=12,
        )

        result = converter.extract_with_result(img)

        assert result.signals.shape == (12, 1000), (
            f"Expected (12, 1000), got {result.signals.shape}"
        )

        # At least 8 of 12 leads should have quality "good" or "warn"
        good_or_warn_count = sum(
            1 for qc in result.per_lead_qc if qc.quality in ("good", "warn")
        )
        assert good_or_warn_count >= 8, (
            f"Expected >= 8 leads with good/warn quality, "
            f"got {good_or_warn_count}/12: "
            f"{[qc.quality for qc in result.per_lead_qc]}"
        )

    def test_inter_lead_correlation_below_threshold(self):
        """
        For a synthetic image with distinct sine frequencies per lead,
        mean pairwise correlation should be < 0.7.

        This catches the bug where np.mean(strip, axis=0) produces nearly
        identical signals for all leads because all strips have similar
        occupancy patterns.
        """
        converter = ECGImageToSignal()
        img, _ = _make_synthetic_ecg_image_with_distinct_leads(
            height=1200, width=1000, num_leads=12,
        )

        result = converter.extract_with_result(img)
        signals = result.signals  # shape: (12, 1000)

        # Compute pairwise Pearson correlations between all lead pairs
        correlations = []
        for i in range(12):
            for j in range(i + 1, 12):
                corr = np.corrcoef(signals[i], signals[j])[0, 1]
                correlations.append(abs(corr))

        mean_corr = float(np.mean(correlations))
        assert mean_corr < 0.7, (
            f"Mean pairwise correlation ({mean_corr:.3f}) should be < 0.7 "
            f"for leads with distinct frequencies. "
            f"This indicates the centroid extraction is not distinguishing "
            f"different traces per lead."
        )
