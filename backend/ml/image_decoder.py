"""
Safe image decoder with security protections.

Layer 0 of ECG Image Pipeline Hardening.
Defends against decompression bombs, handles corrupted images, applies EXIF orientation.
"""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError

from ml.pipeline_types import DecodedImage, PipelineIssue

ImageFile.LOAD_TRUNCATED_IMAGES = False

# Lock to serialize MAX_IMAGE_PIXELS mutations across concurrent decodes.
# Covers the entire decode operation so no thread observes a stale limit.
_pixel_lock = threading.Lock()


class ImageDecodeError(ValueError):
    """Raised when image decoding fails due to format, corruption, or security issues."""

    pass


class ImageProcessingError(RuntimeError):
    """Raised when image processing fails due to server-side issues (not user error)."""

    pass


def safe_decode_image(
    path: str,
    *,
    max_pixels: int,
    max_dimension: int,
    processing_max_dimension: int,
) -> DecodedImage:
    """
    Safely decode an image file with security protections.

    Args:
        path: Path to image file
        max_pixels: Maximum allowed total pixels (width * height)
        max_dimension: Maximum allowed dimension (width or height)
        processing_max_dimension: Maximum dimension for processing (larger images downsampled)

    Returns:
        DecodedImage with RGB array and metadata

    Raises:
        ImageDecodeError: If image is invalid, corrupted, or exceeds limits (user error)
        ImageProcessingError: If processing fails due to server-side issues
    """
    # Temporarily raise Pillow's built-in pixel limit to our configured value
    # so that images above Pillow's default (89M) but below our limit are allowed.
    # The lock serializes the entire decode to prevent concurrent threads from
    # observing or reverting the global mid-operation.
    with _pixel_lock:
        original_max_pixels = Image.MAX_IMAGE_PIXELS
        Image.MAX_IMAGE_PIXELS = max_pixels
        try:
            return _decode_image_inner(
                path,
                max_pixels=max_pixels,
                max_dimension=max_dimension,
                processing_max_dimension=processing_max_dimension,
            )
        finally:
            Image.MAX_IMAGE_PIXELS = original_max_pixels


def _decode_image_inner(
    path: str,
    *,
    max_pixels: int,
    max_dimension: int,
    processing_max_dimension: int,
) -> DecodedImage:
    """Internal decode logic. Called while holding _pixel_lock."""
    try:
        # Read header to check dimensions
        with Image.open(path) as img:
            width, height = img.size

            # Validate dimensions
            if width == 0 or height == 0:
                raise ImageDecodeError("图片尺寸无效：宽或高为零")

            if width * height > max_pixels:
                raise ImageDecodeError(
                    f"图片像素总数超过限制: {width * height:,} > {max_pixels:,}"
                )

            if width > max_dimension or height > max_dimension:
                raise ImageDecodeError(
                    f"图片分辨率超过限制: {width}x{height} (最大允许 {max_dimension})"
                )

            format_name = img.format
            original_mode = img.mode

        # Second pass: decode with EXIF transpose
        with Image.open(path) as img:
            # Check if EXIF orientation tag exists before transpose
            from PIL.ExifTags import Base as ExifBase

            exif_transposed = False
            if hasattr(img, "_getexif") and img._getexif():
                orientation = img._getexif().get(ExifBase.Orientation, None)
                exif_transposed = orientation is not None and orientation != 1

            # Apply EXIF orientation
            img = ImageOps.exif_transpose(img)

            # Convert to RGB
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Downsample BEFORE creating numpy array to limit memory
            if max(img.size) > processing_max_dimension:
                ratio = processing_max_dimension / max(img.size)
                new_size = (
                    max(1, int(img.size[0] * ratio)),
                    max(1, int(img.size[1] * ratio)),
                )
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # Convert to numpy array
            image_rgb = np.array(img, dtype=np.uint8)

            # Get final dimensions
            final_width, final_height = img.size

        return DecodedImage(
            image_rgb=image_rgb,
            width=final_width,
            height=final_height,
            format=format_name,
            mode="RGB",
            exif_transposed=exif_transposed,
            warnings=[],
        )

    except ImageDecodeError:
        raise
    except UnidentifiedImageError:
        raise ImageDecodeError("无法识别的图片格式或文件已损坏")
    except Image.DecompressionBombError as e:
        raise ImageDecodeError(f"图片存在异常解压风险: {str(e)}")
    except MemoryError as e:
        raise ImageProcessingError(f"图片处理内存不足: {str(e)}")
    except OSError as e:
        # Distinguish file corruption (400) from disk/permission errors (500)
        if "cannot identify" in str(e).lower() or "truncated" in str(e).lower():
            raise ImageDecodeError(f"图片文件损坏或解码失败: {str(e)}")
        raise ImageProcessingError(f"文件系统错误: {str(e)}")
    except Exception as e:
        raise ImageDecodeError(f"图片文件损坏或解码失败: {str(e)}")
