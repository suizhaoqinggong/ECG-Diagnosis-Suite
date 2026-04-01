"""
Tests for grid line suppression in ECGImageToSignal.

These tests verify that:
1. Grid lines on colored ECG paper are suppressed
2. Actual ECG traces are preserved
3. Grayscale-only images get conservative/no-op treatment
4. The full extraction pipeline still works after grid suppression
"""

import cv2
import numpy as np
import pytest

from ml.ecg_image_converter import ECGImageToSignal


# ---------------------------------------------------------------------------
# Helpers — synthetic ECG images
# ---------------------------------------------------------------------------

def _make_rgb_image(height=1200, width=1000, bg_color=(255, 255, 255)):
    """Create a blank RGB image with the given background color."""
    img = np.full((height, width, 3), bg_color, dtype=np.uint8)
    return img


def _draw_grid(img, color=(200, 60, 60), spacing=50, thickness=1):
    """Draw horizontal and vertical grid lines like ECG paper."""
    h, w = img.shape[:2]
    # Horizontal lines
    for y in range(0, h, spacing):
        cv2.line(img, (0, y), (w, y), color, thickness)
    # Vertical lines
    for x in range(0, w, spacing):
        cv2.line(img, (x, 0), (x, h), color, thickness)
    return img


def _draw_sine_trace(img, y_center, amplitude=15, frequency=3, color=(0, 0, 0), thickness=2):
    """Draw a sine-wave trace across the image at y_center."""
    h, w = img.shape[:2]
    points = []
    for x in range(w):
        y = int(y_center + amplitude * np.sin(2 * np.pi * frequency * x / w))
        y = np.clip(y, 0, h - 1)
        points.append((x, y))
    for i in range(len(points) - 1):
        cv2.line(img, points[i], points[i + 1], color, thickness)
    return img


def _make_ecg_paper_image(
    height=1200, width=1000, num_leads=12,
    grid_color=(200, 60, 60), trace_color=(0, 0, 0),
    grid_spacing=50, trace_amplitude=15, trace_frequency=3,
):
    """
    Create a synthetic ECG paper image with colored grid and black traces.
    Mimics real ECG paper: pink/red grid, black traces in 12 horizontal strips.
    """
    img = _make_rgb_image(height, width, bg_color=(255, 255, 245))
    _draw_grid(img, color=grid_color, spacing=grid_spacing)

    strip_height = height // num_leads
    for i in range(num_leads):
        y_center = int((i + 0.5) * strip_height)
        _draw_sine_trace(
            img, y_center,
            amplitude=trace_amplitude,
            frequency=trace_frequency,
            color=trace_color,
            thickness=2,
        )
    return img


def _make_grayscale_ecg_image(height=1200, width=1000, num_leads=12):
    """Create a grayscale ECG image with gray grid and dark traces."""
    # Start with a light background
    img = np.full((height, width), 230, dtype=np.uint8)

    # Draw gray grid
    for y in range(0, height, 50):
        img[y, :] = 180
    for x in range(0, width, 50):
        img[:, x] = 180

    # Draw traces
    strip_height = height // num_leads
    for i in range(num_leads):
        y_center = int((i + 0.5) * strip_height)
        for x in range(width):
            y = int(y_center + 15 * np.sin(2 * np.pi * 3 * x / width))
            y = np.clip(y, 0, height - 1)
            img[y, x] = 30  # Dark trace
            if y + 1 < height:
                img[y + 1, x] = 30

    return img


# ---------------------------------------------------------------------------
# Test 1: Synthetic grid on colored paper is suppressed, traces preserved
# ---------------------------------------------------------------------------

class TestGridSuppressionColoredPaper:
    """Grid lines on colored ECG paper should be suppressed."""

    def test_suppress_grid_lines_returns_grayscale(self):
        """_suppress_grid_lines should return a 2-D grayscale array."""
        converter = ECGImageToSignal()
        img = _make_ecg_paper_image(height=600, width=400, num_leads=12)
        result = converter._suppress_grid_lines(img)
        assert result.ndim == 2, f"Expected 2-D output, got shape {result.shape}"

    def test_grid_pixels_have_lower_intensity_after_suppression(self):
        """Grid-only pixels should have higher intensity (suppressed) than trace pixels."""
        converter = ECGImageToSignal()
        img = _make_ecg_paper_image(height=600, width=400, num_leads=12)

        result = converter._suppress_grid_lines(img)

        # Sample a grid-only region (top-left corner area, away from any trace)
        # The grid pixel at (0, 0) is pure grid, no trace
        grid_val = result[0, 0]

        # Find a trace pixel — scan a strip around the center of lead 0
        strip_h = 600 // 12
        trace_y = strip_h // 2
        trace_region = result[trace_y - 5:trace_y + 5, 100:200]
        # Use the darkest pixel in the region as representative of the trace.
        # The trace is a thin line (2px) within a mostly-background region,
        # so np.mean is dominated by bright background pixels.
        trace_val = float(np.min(trace_region))

        # After suppression, grid should be brighter (suppressed) than traces
        # Traces are dark, so grid_val should be much higher than trace values
        # But actually we want traces to survive: trace should be darker than grid
        assert trace_val < grid_val, (
            f"Trace region ({trace_val:.1f}) should be darker than grid ({grid_val:.1f})"
        )

    def test_trace_pixels_survive(self):
        """Black trace pixels should have low values (dark) after suppression."""
        converter = ECGImageToSignal()
        img = _make_ecg_paper_image(height=600, width=400, num_leads=12)
        result = converter._suppress_grid_lines(img)

        # In the center of the first lead strip, trace should be very dark
        strip_h = 600 // 12
        trace_y = strip_h // 2
        center_col = 200  # Middle of image
        trace_pixel = result[trace_y, center_col]

        # The trace pixel should be fairly dark (value < 128)
        assert trace_pixel < 128, f"Trace pixel too bright: {trace_pixel}"


# ---------------------------------------------------------------------------
# Test 2: Grayscale fallback — grayscale-only input is handled conservatively
# ---------------------------------------------------------------------------

class TestGrayscaleFallback:
    """Grayscale-only images should get no-op or conservative suppression."""

    def test_grayscale_3channel_input(self):
        """A 3-channel grayscale image (R==G==B) should be handled gracefully."""
        converter = ECGImageToSignal()
        # Create a 3-channel image where R==G==B
        gray = _make_grayscale_ecg_image(height=600, width=400, num_leads=12)
        img = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        result = converter._suppress_grid_lines(img)

        assert result.ndim == 2
        assert result.shape == (600, 400)

    def test_grayscale_2channel_input(self):
        """A 2-D grayscale image should pass through unchanged."""
        converter = ECGImageToSignal()
        gray = _make_grayscale_ecg_image(height=600, width=400, num_leads=12)
        result = converter._suppress_grid_lines(gray)

        # For a 2-D input, the method should either return it as-is
        # or do minimal processing
        assert result.ndim == 2
        assert result.shape == gray.shape


# ---------------------------------------------------------------------------
# Test 3: Pure grid image — no traces, mostly suppressed
# ---------------------------------------------------------------------------

class TestPureGridImage:
    """An image with only grid lines and no traces should be heavily suppressed."""

    def test_pure_grid_output_has_high_values(self):
        """Most pixels in a pure-grid image should be bright after suppression."""
        converter = ECGImageToSignal()
        img = _make_rgb_image(height=600, width=400, bg_color=(255, 255, 245))
        _draw_grid(img, color=(200, 60, 60), spacing=25, thickness=1)

        result = converter._suppress_grid_lines(img)

        # Most pixels should be bright (grid suppressed)
        mean_val = float(np.mean(result))
        assert mean_val > 100, (
            f"Pure grid image should have high mean after suppression, got {mean_val:.1f}"
        )


# ---------------------------------------------------------------------------
# Test 4: Trace preservation — known dark pixels survive
# ---------------------------------------------------------------------------

class TestTracePreservation:
    """Known trace pixels should survive grid suppression."""

    def test_black_pixels_preserved(self):
        """Pure black pixels (traces) should remain dark after suppression."""
        converter = ECGImageToSignal()
        img = _make_rgb_image(height=200, width=400, bg_color=(255, 255, 245))
        _draw_grid(img, color=(200, 60, 60), spacing=25)

        # Draw a known black line at row 100
        img[100, 50:350, :] = 0

        result = converter._suppress_grid_lines(img)

        # Check that most of the black pixels in that row survived
        black_region = result[100, 50:350]
        dark_pixels = np.sum(black_region < 80)
        total_pixels = len(black_region)

        # At least 80% of the black trace pixels should remain dark
        survival_rate = dark_pixels / total_pixels
        assert survival_rate >= 0.8, (
            f"Only {survival_rate:.0%} of trace pixels survived (need >= 80%)"
        )


# ---------------------------------------------------------------------------
# Test 5: Regression — full pipeline still works
# ---------------------------------------------------------------------------

class TestRegression:
    """Full extraction pipeline should still work after grid suppression."""

    def test_extract_with_result_returns_12_leads(self):
        """extract_with_result should produce 12-lead output from colored ECG image."""
        converter = ECGImageToSignal()
        img = _make_ecg_paper_image(height=1200, width=1000, num_leads=12)
        result = converter.extract_with_result(img)

        assert result.signals.shape == (12, 1000), (
            f"Expected (12, 1000), got {result.signals.shape}"
        )

    def test_extract_with_result_signal_not_constant(self):
        """Extracted signals should not be constant (flatline)."""
        converter = ECGImageToSignal()
        img = _make_ecg_paper_image(height=1200, width=1000, num_leads=12)
        result = converter.extract_with_result(img)

        for i in range(12):
            std = float(np.std(result.signals[i]))
            assert std > 1e-3, f"Lead {i} is nearly constant (std={std:.6f})"

    def test_extract_with_result_grayscale_image(self):
        """Pipeline should also work with grayscale (2-D) input."""
        converter = ECGImageToSignal()
        gray = _make_grayscale_ecg_image(height=1200, width=1000, num_leads=12)
        result = converter.extract_with_result(gray)

        assert result.signals.shape == (12, 1000)

    def test_extract_with_result_overall_quality(self):
        """Overall quality should be pass or warn (not fail) for clean synthetic image."""
        converter = ECGImageToSignal()
        img = _make_ecg_paper_image(height=1200, width=1000, num_leads=12)
        result = converter.extract_with_result(img)

        assert result.overall_quality in ("pass", "warn"), (
            f"Expected pass or warn, got {result.overall_quality}"
        )


# ---------------------------------------------------------------------------
# Test 6: Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases: faint traces, dark background, etc."""

    def test_faint_traces(self):
        """Faint traces (dark gray, not black) should still be preserved."""
        converter = ECGImageToSignal()
        img = _make_rgb_image(height=200, width=400, bg_color=(255, 255, 245))
        _draw_grid(img, color=(200, 60, 60), spacing=25)

        # Draw a faint trace (value 80 — not pure black)
        img[100, 50:350, :] = 80

        result = converter._suppress_grid_lines(img)

        # Faint trace should still be visible (darker than background)
        trace_val = float(np.mean(result[100, 50:350]))
        bg_val = float(np.mean(result[50, 50:350]))  # A region with no trace

        assert trace_val < bg_val, (
            f"Faint trace ({trace_val:.1f}) should be darker than bg ({bg_val:.1f})"
        )

    def test_small_image(self):
        """Very small image should not crash."""
        converter = ECGImageToSignal()
        img = _make_rgb_image(height=48, width=48, bg_color=(255, 255, 245))
        _draw_grid(img, color=(200, 60, 60), spacing=12)
        img[24, 10:38, :] = 0  # Small trace

        result = converter._suppress_grid_lines(img)
        assert result.ndim == 2
        assert result.shape == (48, 48)

    def test_white_background_no_grid(self):
        """A plain white image with no grid should not crash."""
        converter = ECGImageToSignal()
        img = _make_rgb_image(height=200, width=400, bg_color=(255, 255, 255))

        result = converter._suppress_grid_lines(img)
        assert result.ndim == 2

        # Should be mostly white
        assert float(np.mean(result)) > 200

    def test_dark_background(self):
        """Dark background image should not crash (e.g., inverted ECG)."""
        converter = ECGImageToSignal()
        img = _make_rgb_image(height=200, width=400, bg_color=(20, 20, 30))
        # Light trace on dark bg
        img[100, 50:350, :] = 200

        result = converter._suppress_grid_lines(img)
        assert result.ndim == 2
        assert result.shape == (200, 400)

    def test_suppression_safe_guard(self):
        """If suppression would remove >50% of content, it should be skipped."""
        converter = ECGImageToSignal()
        # Create an image that is mostly dark (like an inverted ECG)
        img = np.zeros((200, 400, 3), dtype=np.uint8)
        # Draw a colored grid on top
        for y in range(0, 200, 20):
            img[y, :, :] = (100, 40, 40)

        # This should not crash and should not wipe everything out
        result = converter._suppress_grid_lines(img)
        assert result.ndim == 2
        # Result should not be entirely zeroed out
        assert float(np.mean(result)) > 0
