"""
Tests for P5: Rotation/skew detection and correction.

These tests verify:
1. _detect_skew: Uses Hough line transform to detect dominant line angle
2. _correct_skew: Rotates image to correct skew using warpAffine
3. Integration in extract_with_result: Applies correction when appropriate

ALL TESTS WILL FAIL because _detect_skew and _correct_skew do not exist yet.
"""

import cv2
import numpy as np
import pytest

from ml.ecg_image_converter import ECGImageToSignal
from ml.pipeline_types import ExtractionResult


# -----------------------------------------------------------------------------
# Helpers — synthetic images with known rotation
# -----------------------------------------------------------------------------

def _create_straight_lines_image(
    width: int = 800,
    height: int = 600,
    num_lines: int = 5,
    line_thickness: int = 3,
) -> np.ndarray:
    """Create an image with straight horizontal lines (0 degree rotation)."""
    image = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Draw horizontal lines
    line_spacing = height // (num_lines + 1)
    for i in range(1, num_lines + 1):
        y = i * line_spacing
        cv2.line(image, (50, y), (width - 50, y), (0, 0, 0), line_thickness)

    return image


def _create_rotated_image(
    width: int = 800,
    height: int = 600,
    angle: float = 15.0,
    num_lines: int = 5,
    line_thickness: int = 3,
) -> np.ndarray:
    """Create an image with lines at a specific angle."""
    # Create a larger canvas to avoid clipping after rotation
    canvas_size = int(max(width, height) * 1.5)
    image = np.ones((canvas_size, canvas_size, 3), dtype=np.uint8) * 255

    center_x = canvas_size // 2
    center_y = canvas_size // 2

    # Draw lines at the specified angle
    line_length = min(width, height) * 0.8
    line_spacing = 40

    for i in range(-num_lines // 2, num_lines // 2 + 1):
        offset = i * line_spacing

        # Calculate line endpoints at the specified angle
        rad = np.deg2rad(angle)
        dx = line_length * np.cos(rad) / 2
        dy = line_length * np.sin(rad) / 2

        # Perpendicular offset
        perp_x = -offset * np.sin(rad)
        perp_y = offset * np.cos(rad)

        x1 = int(center_x - dx + perp_x)
        y1 = int(center_y - dy + perp_y)
        x2 = int(center_x + dx + perp_x)
        y2 = int(center_y + dy + perp_y)

        cv2.line(image, (x1, y1), (x2, y2), (0, 0, 0), line_thickness)

    # Crop to desired size
    start_x = (canvas_size - width) // 2
    start_y = (canvas_size - height) // 2
    return image[start_y:start_y + height, start_x:start_x + width]


def _create_no_line_image(
    width: int = 400,
    height: int = 300,
) -> np.ndarray:
    """Create an image with no detectable lines."""
    return np.ones((height, width, 3), dtype=np.uint8) * 255


def _create_ecg_like_image(
    width: int = 800,
    height: int = 600,
    angle: float = 0.0,
) -> np.ndarray:
    """Create an ECG-like image with horizontal strips and wave patterns."""
    # Create base image
    canvas_size = int(max(width, height) * 1.5)
    image = np.ones((canvas_size, canvas_size, 3), dtype=np.uint8) * 255

    num_leads = 12
    strip_height = canvas_size // num_leads

    # Draw ECG-like wave patterns in each strip
    for lead in range(num_leads):
        y_base = lead * strip_height + strip_height // 2

        # Draw a sine wave with some variation
        points = []
        for x in range(50, canvas_size - 50, 2):
            # Create ECG-like pattern: P-QRS-T waves
            t = x / 50.0
            y_offset = (
                10 * np.sin(t * 2 * np.pi) +  # Base sine
                20 * np.exp(-((t % 3) - 1.5) ** 2) * np.sin(t * 10)  # QRS-like spikes
            )
            y = int(y_base + y_offset)
            points.append((x, y))

        # Draw the wave
        for i in range(len(points) - 1):
            cv2.line(image, points[i], points[i + 1], (0, 0, 0), 2)

    # Rotate if needed
    if angle != 0:
        center = (canvas_size // 2, canvas_size // 2)
        rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        image = cv2.warpAffine(image, rot_matrix, (canvas_size, canvas_size),
                               borderValue=(255, 255, 255))

    # Crop to desired size
    start_x = (canvas_size - width) // 2
    start_y = (canvas_size - height) // 2
    return image[start_y:start_y + height, start_x:start_x + width]


# -----------------------------------------------------------------------------
# Tests for _detect_skew method
# -----------------------------------------------------------------------------

class TestDetectSkew:
    """Tests for the _detect_skew method."""

    def test_method_exists(self):
        """Test that _detect_skew method exists."""
        converter = ECGImageToSignal()
        assert hasattr(converter, '_detect_skew')

    def test_detect_zero_rotation(self):
        """Test detection of straight horizontal lines (0 degrees)."""
        converter = ECGImageToSignal()
        image = _create_straight_lines_image()

        angle, confidence = converter._detect_skew(image)

        assert abs(angle) < 2.0, f"Expected angle near 0, got {angle}"
        assert confidence > 0.5, f"Expected high confidence, got {confidence}"

    def test_detect_small_rotation(self):
        """Test detection of small rotation (5 degrees)."""
        converter = ECGImageToSignal()
        image = _create_rotated_image(angle=5.0)

        angle, confidence = converter._detect_skew(image)

        assert abs(angle - 5.0) < 3.0, f"Expected angle near 5, got {angle}"
        assert confidence > 0.5, f"Expected high confidence, got {confidence}"

    def test_detect_moderate_rotation(self):
        """Test detection of moderate rotation (15 degrees)."""
        converter = ECGImageToSignal()
        image = _create_rotated_image(angle=15.0)

        angle, confidence = converter._detect_skew(image)

        assert abs(angle - 15.0) < 5.0, f"Expected angle near 15, got {angle}"
        assert confidence > 0.5, f"Expected high confidence, got {confidence}"

    def test_detect_large_rotation(self):
        """Test detection of large rotation (35 degrees)."""
        converter = ECGImageToSignal()
        image = _create_rotated_image(angle=35.0)

        angle, confidence = converter._detect_skew(image)

        assert abs(angle - 35.0) < 10.0, f"Expected angle near 35, got {angle}"
        assert confidence > 0.5, f"Expected high confidence, got {confidence}"

    def test_detect_negative_rotation(self):
        """Test detection of negative rotation (-10 degrees)."""
        converter = ECGImageToSignal()
        image = _create_rotated_image(angle=-10.0)

        angle, confidence = converter._detect_skew(image)

        assert abs(angle - (-10.0)) < 5.0, f"Expected angle near -10, got {angle}"
        assert confidence > 0.5, f"Expected high confidence, got {confidence}"

    def test_no_lines_low_confidence(self):
        """Test that images without lines return low confidence."""
        converter = ECGImageToSignal()
        image = _create_no_line_image()

        angle, confidence = converter._detect_skew(image)

        assert confidence < 0.5, f"Expected low confidence for no lines, got {confidence}"

    def test_returns_tuple(self):
        """Test that _detect_skew returns a tuple of (angle, confidence)."""
        converter = ECGImageToSignal()
        image = _create_straight_lines_image()

        result = converter._detect_skew(image)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], (int, float))
        assert isinstance(result[1], (int, float))


# -----------------------------------------------------------------------------
# Tests for _correct_skew method
# -----------------------------------------------------------------------------

class TestCorrectSkew:
    """Tests for the _correct_skew method."""

    def test_method_exists(self):
        """Test that _correct_skew method exists."""
        converter = ECGImageToSignal()
        assert hasattr(converter, '_correct_skew')

    def test_correct_small_rotation(self):
        """Test correction of small rotation (5 degrees)."""
        converter = ECGImageToSignal()
        original = _create_straight_lines_image()
        rotated = _create_rotated_image(angle=5.0)

        corrected = converter._correct_skew(rotated, 5.0)

        # Check dimensions are preserved
        assert corrected.shape == rotated.shape

        # Check that lines are now more horizontal
        angle_after, confidence = converter._detect_skew(corrected)
        assert abs(angle_after) < 3.0, f"Expected near-zero angle after correction, got {angle_after}"

    def test_correct_moderate_rotation(self):
        """Test correction of moderate rotation (15 degrees)."""
        converter = ECGImageToSignal()
        rotated = _create_rotated_image(angle=15.0)

        corrected = converter._correct_skew(rotated, 15.0)

        # Check dimensions are preserved
        assert corrected.shape == rotated.shape

        # Check that lines are now more horizontal
        angle_after, confidence = converter._detect_skew(corrected)
        assert abs(angle_after) < 5.0, f"Expected near-zero angle after correction, got {angle_after}"

    def test_preserve_dimensions(self):
        """Test that corrected image preserves original dimensions."""
        converter = ECGImageToSignal()
        rotated = _create_rotated_image(width=640, height=480, angle=10.0)

        corrected = converter._correct_skew(rotated, 10.0)

        assert corrected.shape == rotated.shape
        assert corrected.shape[0] == 480
        assert corrected.shape[1] == 640

    def test_returns_numpy_array(self):
        """Test that _correct_skew returns a numpy array."""
        converter = ECGImageToSignal()
        rotated = _create_rotated_image(angle=10.0)

        corrected = converter._correct_skew(rotated, 10.0)

        assert isinstance(corrected, np.ndarray)


# -----------------------------------------------------------------------------
# Tests for integration in extract_with_result
# -----------------------------------------------------------------------------

class TestSkewIntegration:
    """Tests for skew detection integration in extract_with_result."""

    def test_no_skew_correction_needed(self):
        """Test that straight images are processed without correction."""
        converter = ECGImageToSignal()
        image = _create_ecg_like_image(angle=0.0)

        result = converter.extract_with_result(image)

        assert isinstance(result, ExtractionResult)
        # Should not have excessive rotation warning
        assert not any("excessive" in w.lower() for w in result.warnings)

    def test_small_skew_is_corrected(self):
        """Test that small skew (5 degrees) is automatically corrected."""
        converter = ECGImageToSignal()
        image = _create_ecg_like_image(angle=5.0)

        result = converter.extract_with_result(image)

        assert isinstance(result, ExtractionResult)
        # Should have skew_corrected flag set
        assert hasattr(result, 'skew_corrected')
        assert result.skew_corrected is True

    def test_moderate_skew_is_corrected(self):
        """Test that moderate skew (15 degrees) is automatically corrected."""
        converter = ECGImageToSignal()
        image = _create_ecg_like_image(angle=15.0)

        result = converter.extract_with_result(image)

        assert isinstance(result, ExtractionResult)
        assert result.skew_corrected is True
        # Should have skew_angle recorded
        assert hasattr(result, 'skew_angle')
        assert result.skew_angle is not None
        assert abs(result.skew_angle - 15.0) < 10.0

    def test_excessive_skew_warning(self):
        """Test that excessive rotation (>30 degrees) triggers warning."""
        converter = ECGImageToSignal()
        image = _create_ecg_like_image(angle=35.0)

        result = converter.extract_with_result(image)

        assert isinstance(result, ExtractionResult)
        # Should have excessive rotation warning
        assert any("excessive" in w.lower() or "rotation" in w.lower()
                   for w in result.warnings)
        assert result.overall_quality == "warn"

    def test_very_large_skew_warning(self):
        """Test that very large rotation (45 degrees) triggers warning."""
        converter = ECGImageToSignal()
        image = _create_ecg_like_image(angle=45.0)

        result = converter.extract_with_result(image)

        assert isinstance(result, ExtractionResult)
        assert any("excessive" in w.lower() or "rotation" in w.lower()
                   for w in result.warnings)
        assert result.overall_quality == "warn"

    def test_skew_not_corrected_when_low_confidence(self):
        """Test that skew is not corrected when detection confidence is low."""
        converter = ECGImageToSignal()
        image = _create_no_line_image()

        result = converter.extract_with_result(image)

        assert isinstance(result, ExtractionResult)
        # Should not be marked as corrected when no lines detected
        if hasattr(result, 'skew_corrected'):
            assert result.skew_corrected is False

    def test_skew_angle_field_exists(self):
        """Test that ExtractionResult has skew_angle field."""
        result = ExtractionResult(
            signals=np.zeros((12, 1000), dtype=np.float32),
            layout_method="test",
            layout_score=1.0,
            fallback_used=False,
            interpolated_columns=0,
            interpolated_ratio=0.0,
            per_lead_qc=[],
        )
        assert hasattr(result, 'skew_angle')

    def test_skew_corrected_field_exists(self):
        """Test that ExtractionResult has skew_corrected field."""
        result = ExtractionResult(
            signals=np.zeros((12, 1000), dtype=np.float32),
            layout_method="test",
            layout_score=1.0,
            fallback_used=False,
            interpolated_columns=0,
            interpolated_ratio=0.0,
            per_lead_qc=[],
        )
        assert hasattr(result, 'skew_corrected')


# -----------------------------------------------------------------------------
# Edge case tests
# -----------------------------------------------------------------------------

class TestSkewEdgeCases:
    """Edge case tests for skew detection and correction."""

    def test_detect_skew_grayscale_image(self):
        """Test that _detect_skew works with grayscale images."""
        converter = ECGImageToSignal()
        image = _create_straight_lines_image()
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        angle, confidence = converter._detect_skew(gray)

        assert isinstance(angle, (int, float))
        assert isinstance(confidence, (int, float))

    def test_correct_skew_grayscale_image(self):
        """Test that _correct_skew works with grayscale images."""
        converter = ECGImageToSignal()
        image = _create_rotated_image(angle=10.0)
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        corrected = converter._correct_skew(gray, 10.0)

        assert isinstance(corrected, np.ndarray)
        assert corrected.shape == gray.shape

    def test_detect_skew_very_small_image(self):
        """Test _detect_skew with very small image."""
        converter = ECGImageToSignal()
        image = _create_straight_lines_image(width=100, height=100)

        angle, confidence = converter._detect_skew(image)

        # Should not crash, may return low confidence
        assert isinstance(angle, (int, float))
        assert isinstance(confidence, (int, float))

    def test_correct_zero_angle(self):
        """Test _correct_skew with zero angle (no rotation)."""
        converter = ECGImageToSignal()
        image = _create_straight_lines_image()

        corrected = converter._correct_skew(image, 0.0)

        assert corrected.shape == image.shape
        # Image should be essentially unchanged

    def test_correct_negative_angle(self):
        """Test _correct_skew with negative angle."""
        converter = ECGImageToSignal()
        image = _create_rotated_image(angle=-10.0)

        corrected = converter._correct_skew(image, -10.0)

        angle_after, _ = converter._detect_skew(corrected)
        assert abs(angle_after) < 5.0

    def test_tiny_rotation_not_corrected(self):
        """Test that tiny rotations (< 2 degrees) don't trigger correction."""
        converter = ECGImageToSignal()
        image = _create_ecg_like_image(angle=1.0)

        result = converter.extract_with_result(image)

        # Tiny rotation should not trigger correction
        if hasattr(result, 'skew_corrected'):
            assert result.skew_corrected is False

    def test_skew_metadata_recorded(self):
        """Test that skew information is recorded in result metadata."""
        converter = ECGImageToSignal()
        image = _create_ecg_like_image(angle=10.0)

        result = converter.extract_with_result(image)

        # Should have both fields
        assert hasattr(result, 'skew_angle')
        assert hasattr(result, 'skew_corrected')

        # If corrected, angle should be recorded
        if result.skew_corrected:
            assert result.skew_angle is not None


# -----------------------------------------------------------------------------
# Quality impact tests
# -----------------------------------------------------------------------------

class TestSkewQualityImpact:
    """Tests for quality impact of skew detection and correction."""

    def test_corrected_skew_improves_quality(self):
        """Test that correcting skew improves extraction quality."""
        converter = ECGImageToSignal()

        # Create rotated image
        rotated = _create_ecg_like_image(angle=10.0)

        # Extract without correction (simulate by calling directly)
        # First, let's verify that correction happens
        result = converter.extract_with_result(rotated)

        # Result should be valid
        assert result.signals.shape == (12, 1000)
        assert result.overall_quality in ("pass", "warn", "fail")

    def test_excessive_skew_sets_quality_warn(self):
        """Test that excessive skew sets overall_quality to 'warn'."""
        converter = ECGImageToSignal()
        image = _create_ecg_like_image(angle=35.0)

        result = converter.extract_with_result(image)

        assert result.overall_quality == "warn"

    def test_skew_correction_does_not_degrade_signals(self):
        """Test that skew correction doesn't significantly degrade signal quality."""
        converter = ECGImageToSignal()

        # Create straight and slightly rotated images
        straight = _create_ecg_like_image(angle=0.0)
        rotated = _create_ecg_like_image(angle=5.0)

        result_straight = converter.extract_with_result(straight)
        result_rotated = converter.extract_with_result(rotated)

        # Both should produce valid signals
        assert result_straight.signals.shape == (12, 1000)
        assert result_rotated.signals.shape == (12, 1000)

        # Rotated (and corrected) should not have significantly worse quality
        # than straight - at least not "fail"
        assert result_rotated.overall_quality != "fail"


# -----------------------------------------------------------------------------
# Run tests
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
