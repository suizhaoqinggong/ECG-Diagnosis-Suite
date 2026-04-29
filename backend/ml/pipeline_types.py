"""
Pipeline types for ECG image processing.

Data structures used across the image processing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

IssueSeverity = Literal["info", "warning", "error"]
LeadQuality = Literal["good", "warn", "poor", "fail"]
OverallQuality = Literal["pass", "warn", "fail"]


@dataclass
class PipelineIssue:
    """Represents an issue or warning in the processing pipeline."""

    code: str
    message: str
    severity: IssueSeverity
    metric_name: str | None = None
    metric_value: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecodedImage:
    """Result of safe image decoding."""

    image_rgb: NDArray[np.uint8]
    width: int
    height: int
    format: str | None
    mode: str
    exif_transposed: bool
    warnings: list[PipelineIssue] = field(default_factory=list)


@dataclass
class ValidationMetrics:
    """Metrics collected during image validation."""

    dark_pixel_ratio: float
    content_band_count: int
    aspect_ratio: float
    foreground_rows_ratio: float
    foreground_cols_ratio: float


@dataclass
class ValidationResult:
    """Result of ECG image validation."""

    accepted: bool
    metrics: ValidationMetrics
    issues: list[PipelineIssue] = field(default_factory=list)


@dataclass
class LeadQC:
    """Quality control metrics for a single ECG lead."""

    lead_index: int
    flatness: float
    coverage: float
    valid_column_ratio: float
    interpolated_ratio: float
    jump_rate: float
    clipped_ratio: float
    snr_estimate: float | None
    quality: LeadQuality
    warnings: list[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    """Result of ECG signal extraction from image."""

    signals: NDArray[np.float32]
    layout_method: str
    layout_score: float
    fallback_used: bool
    interpolated_columns: int
    interpolated_ratio: float
    per_lead_qc: list[LeadQC]
    warnings: list[str] = field(default_factory=list)
    issues: list[PipelineIssue] = field(default_factory=list)
    overall_quality: OverallQuality = "pass"
    skew_angle: float | None = None
    skew_corrected: bool = False
