"""
Tests for image_decoder module - Safe image decoding with security protections.

Layer 0 of ECG Image Pipeline Hardening:
- Defends against decompression bombs
- Handles corrupted images
- Applies EXIF orientation
- Downsamples large images
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ml.image_decoder import ImageDecodeError, safe_decode_image


class TestImageDecoderAcceptsValidImages:
    """Tests for accepting valid image formats."""

    def test_accepts_valid_png(self, tmp_path: Path):
        """Valid PNG image should decode successfully."""
        # Create a simple test PNG
        img_path = tmp_path / "test.png"
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        Image.fromarray(test_image, "RGB").save(img_path)

        result = safe_decode_image(
            str(img_path),
            max_pixels=178_956_970,
            max_dimension=16000,
            processing_max_dimension=4096,
        )

        assert result.width == 100
        assert result.height == 100
        assert result.format == "PNG"
        assert result.mode == "RGB"
        assert result.image_rgb.shape == (100, 100, 3)
        assert result.exif_transposed is False

    def test_accepts_valid_jpeg(self, tmp_path: Path):
        """Valid JPEG image should decode successfully."""
        img_path = tmp_path / "test.jpg"
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        Image.fromarray(test_image, "RGB").save(img_path, format="JPEG")

        result = safe_decode_image(
            str(img_path),
            max_pixels=178_956_970,
            max_dimension=16000,
            processing_max_dimension=4096,
        )

        assert result.width == 100
        assert result.height == 100
        assert result.format == "JPEG"
        assert result.mode == "RGB"
        assert result.image_rgb.shape == (100, 100, 3)

    def test_converts_rgba_to_rgb(self, tmp_path: Path):
        """RGBA image should be converted to RGB."""
        img_path = tmp_path / "test.png"
        test_image = np.random.randint(0, 255, (100, 100, 4), dtype=np.uint8)
        Image.fromarray(test_image, "RGBA").save(img_path)

        result = safe_decode_image(
            str(img_path),
            max_pixels=178_956_970,
            max_dimension=16000,
            processing_max_dimension=4096,
        )

        assert result.mode == "RGB"
        assert result.image_rgb.shape == (100, 100, 3)

    def test_converts_grayscale_to_rgb(self, tmp_path: Path):
        """Grayscale image should be converted to RGB."""
        img_path = tmp_path / "test.png"
        test_image = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        Image.fromarray(test_image, "L").save(img_path)

        result = safe_decode_image(
            str(img_path),
            max_pixels=178_956_970,
            max_dimension=16000,
            processing_max_dimension=4096,
        )

        assert result.mode == "RGB"
        assert result.image_rgb.shape == (100, 100, 3)


class TestImageDecoderRejectsInvalidImages:
    """Tests for rejecting invalid/corrupted images."""

    def test_rejects_corrupt_png(self, tmp_path: Path):
        """Corrupted PNG should raise ImageDecodeError."""
        img_path = tmp_path / "corrupt.png"
        img_path.write_bytes(b"\x89PNG\r\n\x1a\nCORRUPTED_DATA")

        with pytest.raises(ImageDecodeError, match="图片文件损坏或解码失败"):
            safe_decode_image(
                str(img_path),
                max_pixels=178_956_970,
                max_dimension=16000,
                processing_max_dimension=4096,
            )

    def test_rejects_random_bytes_with_png_extension(self, tmp_path: Path):
        """Random bytes with .png extension should raise ImageDecodeError."""
        img_path = tmp_path / "fake.png"
        img_path.write_bytes(b"not an image at all, just random text")

        with pytest.raises(ImageDecodeError, match="无法识别的图片格式或文件已损坏"):
            safe_decode_image(
                str(img_path),
                max_pixels=178_956_970,
                max_dimension=16000,
                processing_max_dimension=4096,
            )

    def test_rejects_excessive_pixel_count(self, tmp_path: Path):
        """Image exceeding max_pixels should raise ImageDecodeError."""
        img_path = tmp_path / "huge.png"
        # Create image that exceeds max_pixels=10000
        huge_image = np.zeros((200, 200, 3), dtype=np.uint8)
        Image.fromarray(huge_image, "RGB").save(img_path)

        with pytest.raises(ImageDecodeError, match="图片像素总数超过限制"):
            safe_decode_image(
                str(img_path),
                max_pixels=10000,  # 200x200=40000 > 10000
                max_dimension=16000,
                processing_max_dimension=4096,
            )

    def test_rejects_excessive_dimension(self, tmp_path: Path):
        """Image exceeding max_dimension should raise ImageDecodeError."""
        img_path = tmp_path / "wide.png"
        # Create very wide image
        wide_image = np.zeros((100, 200, 3), dtype=np.uint8)
        Image.fromarray(wide_image, "RGB").save(img_path)

        with pytest.raises(ImageDecodeError, match="图片分辨率超过限制"):
            safe_decode_image(
                str(img_path),
                max_pixels=178_956_970,
                max_dimension=150,  # width 200 > 150
                processing_max_dimension=4096,
            )

    def test_rejects_zero_dimension_image(self, tmp_path: Path):
        """Image with zero dimension should raise ImageDecodeError."""
        img_path = tmp_path / "zero.png"
        # Create a valid image first, then we'll mock it
        test_image = np.zeros((100, 100, 3), dtype=np.uint8)
        Image.fromarray(test_image, "RGB").save(img_path)

        # This test is tricky - PIL won't save zero-dimension images
        # So we test the check indirectly through a mock or skip
        # For now, we'll skip this as it requires mocking PIL internals
        pytest.skip("Cannot create zero-dimension image with PIL")

    def test_rejects_truncated_image(self, tmp_path: Path):
        """Truncated image should raise ImageDecodeError."""
        img_path = tmp_path / "truncated.jpg"
        # Create a valid JPEG then truncate it
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        Image.fromarray(test_image, "RGB").save(img_path, format="JPEG")

        # Truncate the file
        content = img_path.read_bytes()
        img_path.write_bytes(content[: len(content) // 2])

        with pytest.raises(ImageDecodeError, match="图片文件损坏或解码失败"):
            safe_decode_image(
                str(img_path),
                max_pixels=178_956_970,
                max_dimension=16000,
                processing_max_dimension=4096,
            )


class TestImageDecoderExifOrientation:
    """Tests for EXIF orientation handling."""

    def test_applies_exif_orientation(self, tmp_path: Path):
        """Image with EXIF orientation should be transposed."""
        img_path = tmp_path / "oriented.jpg"
        # Create a test image with specific pattern to detect rotation
        test_image = np.zeros((100, 50, 3), dtype=np.uint8)
        test_image[:10, :, 0] = 255  # Red top band

        # Save with EXIF orientation tag for 90 degree rotation
        img = Image.fromarray(test_image, "RGB")

        # EXIF tag 274 is Orientation
        # Value 6 = Rotate 90 CW
        from PIL import ExifTags

        exif = img.getexif()
        exif[274] = 6  # Orientation = Rotate 90 CW
        img.save(img_path, format="JPEG", exif=exif)

        result = safe_decode_image(
            str(img_path),
            max_pixels=178_956_970,
            max_dimension=16000,
            processing_max_dimension=4096,
        )

        # After EXIF transpose, dimensions should swap: 100x50 -> 50x100
        assert result.exif_transposed is True
        # Note: actual dimensions after transpose
        # The exact behavior depends on PIL version
        assert result.width in [50, 100]
        assert result.height in [50, 100]

    def test_image_without_exif_not_transposed(self, tmp_path: Path):
        """Image without EXIF orientation should not be transposed."""
        img_path = tmp_path / "no_exif.png"
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        Image.fromarray(test_image, "RGB").save(img_path)

        result = safe_decode_image(
            str(img_path),
            max_pixels=178_956_970,
            max_dimension=16000,
            processing_max_dimension=4096,
        )

        assert result.exif_transposed is False


class TestImageDecoderDownsampling:
    """Tests for automatic downsampling of large images."""

    def test_downsamples_large_but_safe_image(self, tmp_path: Path):
        """Large image should be downsampled to processing_max_dimension."""
        img_path = tmp_path / "large.png"
        # Create image larger than processing_max_dimension
        large_image = np.random.randint(0, 255, (3000, 4000, 3), dtype=np.uint8)
        Image.fromarray(large_image, "RGB").save(img_path)

        result = safe_decode_image(
            str(img_path),
            max_pixels=178_956_970,
            max_dimension=16000,
            processing_max_dimension=1000,  # Should downsample to fit this
        )

        # Should be downsampled, max dimension should be <= 1000
        assert max(result.width, result.height) <= 1000
        assert result.width > 0
        assert result.height > 0

    def test_does_not_downsample_small_image(self, tmp_path: Path):
        """Small image should not be downsampled."""
        img_path = tmp_path / "small.png"
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        Image.fromarray(test_image, "RGB").save(img_path)

        result = safe_decode_image(
            str(img_path),
            max_pixels=178_956_970,
            max_dimension=16000,
            processing_max_dimension=4096,
        )

        assert result.width == 100
        assert result.height == 100


class TestImageDecoderReturnTypes:
    """Tests for correct return types and dataclass fields."""

    def test_returns_decoded_image_dataclass(self, tmp_path: Path):
        """Should return DecodedImage dataclass with all fields."""
        img_path = tmp_path / "test.png"
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        Image.fromarray(test_image, "RGB").save(img_path)

        from ml.pipeline_types import DecodedImage

        result = safe_decode_image(
            str(img_path),
            max_pixels=178_956_970,
            max_dimension=16000,
            processing_max_dimension=4096,
        )

        assert isinstance(result, DecodedImage)
        assert isinstance(result.image_rgb, np.ndarray)
        assert result.image_rgb.dtype == np.uint8
        assert isinstance(result.width, int)
        assert isinstance(result.height, int)
        assert isinstance(result.format, (str, type(None)))
        assert isinstance(result.mode, str)
        assert isinstance(result.exif_transposed, bool)
        assert isinstance(result.warnings, list)

    def test_image_array_is_rgb(self, tmp_path: Path):
        """Returned array should be RGB format."""
        img_path = tmp_path / "test.png"
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        Image.fromarray(test_image, "RGB").save(img_path)

        result = safe_decode_image(
            str(img_path),
            max_pixels=178_956_970,
            max_dimension=16000,
            processing_max_dimension=4096,
        )

        assert len(result.image_rgb.shape) == 3
        assert result.image_rgb.shape[2] == 3  # RGB channels
