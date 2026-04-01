"""
ECG image input validator.

Layer 1 of ECG Image Pipeline Hardening.
Distinguishes clearly non-ECG images from valid ECGs using heuristic checks.
"""

from __future__ import annotations

import cv2
import numpy as np

from ml.pipeline_types import PipelineIssue, ValidationMetrics, ValidationResult


def validate_ecg_image(image_rgb: np.ndarray) -> ValidationResult:
    """
    Validate that an image appears to be a valid ECG printout.

    Uses heuristic checks on aspect ratio, content density, and horizontal
    structure.  Returns a dual-track result:
      - hard rejects (severity="error") -> the caller should return HTTP 400
      - soft warnings (severity="warning") -> accepted, but quality may be low

    Args:
        image_rgb: RGB image as (H, W, 3) uint8 array.

    Returns:
        ValidationResult with metrics and issues list.
    """
    height, width = image_rgb.shape[:2]
    aspect_ratio = width / max(height, 1)

    # Convert to grayscale, apply CLAHE for contrast enhancement,
    # then OTSU threshold — matching the approach used by the converter.
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_enhanced = clahe.apply(gray)
    _, binary = cv2.threshold(
        gray_enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )

    # Dark pixel ratio (foreground content)
    dark_pixel_ratio = float(np.mean(binary > 0))

    # Row-level foreground analysis
    row_foreground = np.mean(binary > 0, axis=1)
    foreground_rows_ratio = float(np.mean(row_foreground > 0.02))

    # Content band detection via horizontal projection
    content_band_count = _count_content_bands(row_foreground)

    # Column-level foreground
    col_foreground = np.mean(binary > 0, axis=0)
    foreground_cols_ratio = float(np.mean(col_foreground > 0.02))

    metrics = ValidationMetrics(
        dark_pixel_ratio=dark_pixel_ratio,
        content_band_count=content_band_count,
        aspect_ratio=aspect_ratio,
        foreground_rows_ratio=foreground_rows_ratio,
        foreground_cols_ratio=foreground_cols_ratio,
    )

    issues: list[PipelineIssue] = []

    # --- Hard rejects (severity="error") ---

    # Aspect ratio
    if aspect_ratio < 0.3 or aspect_ratio > 5.0:
        issues.append(PipelineIssue(
            code="aspect_ratio_out_of_range",
            message="图片宽高比异常，疑似非心电图。",
            severity="error",
            metric_name="aspect_ratio",
            metric_value=aspect_ratio,
        ))

    # Content density: too blank (lowered threshold to avoid rejecting thin-line ECGs)
    if dark_pixel_ratio < 0.001:
        issues.append(PipelineIssue(
            code="too_blank",
            message="图片内容过少，未检测到有效心电图痕迹。",
            severity="error",
            metric_name="dark_pixel_ratio",
            metric_value=dark_pixel_ratio,
        ))
    elif dark_pixel_ratio > 0.75:
        issues.append(PipelineIssue(
            code="too_dense",
            message="图片内容过密，疑似非标准心电图或拍摄异常。",
            severity="error",
            metric_name="dark_pixel_ratio",
            metric_value=dark_pixel_ratio,
        ))
    elif dark_pixel_ratio > 0.30 and content_band_count <= 2:
        # High density with no band structure = noise/photograph, not ECG
        issues.append(PipelineIssue(
            code="no_ecg_structure",
            message="图片缺乏心电图导联带状结构，疑似非心电图图像。",
            severity="error",
            metric_name="dark_pixel_ratio",
            metric_value=dark_pixel_ratio,
        ))
    elif dark_pixel_ratio < 0.01 or dark_pixel_ratio > 0.60:
        # Borderline density: soft warning
        issues.append(PipelineIssue(
            code="density_borderline",
            message="图片内容密度处于边界范围，结果可靠性可能下降。",
            severity="warning",
            metric_name="dark_pixel_ratio",
            metric_value=dark_pixel_ratio,
        ))

    # Horizontal structure
    if content_band_count == 0:
        issues.append(PipelineIssue(
            code="no_horizontal_structure",
            message="未检测到心电图导联带状结构。",
            severity="error",
            metric_name="content_band_count",
            metric_value=0.0,
        ))
    elif content_band_count < 3:
        # Few bands AND high density → not ECG (e.g. random noise)
        if content_band_count <= 2 and dark_pixel_ratio > 0.20:
            issues.append(PipelineIssue(
                code="no_horizontal_structure",
                message="图片缺乏心电图导联带状结构，疑似非心电图图像。",
                severity="error",
                metric_name="content_band_count",
                metric_value=float(content_band_count),
            ))
        else:
            issues.append(PipelineIssue(
                code="too_few_content_bands",
                message="检测到的导联带数量过少，可能不是标准12导联心电图。",
                severity="warning",
                metric_name="content_band_count",
                metric_value=float(content_band_count),
            ))

    # Minimum resolution
    if min(height, width) < 400:
        issues.append(PipelineIssue(
            code="resolution_too_low",
            message="图片分辨率过低，无法可靠提取心电图信号。",
            severity="error",
            metric_name="min_dimension",
            metric_value=float(min(height, width)),
        ))

    accepted = not any(i.severity == "error" for i in issues)

    return ValidationResult(accepted=accepted, metrics=metrics, issues=issues)


def _count_content_bands(row_foreground: np.ndarray) -> int:
    """Count distinct horizontal content bands in the row projection."""
    in_band = False
    count = 0
    for val in row_foreground:
        if val > 0.05 and not in_band:
            in_band = True
            count += 1
        elif val <= 0.05:
            in_band = False
    return count
