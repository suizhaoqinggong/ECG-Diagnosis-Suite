from __future__ import annotations

from pathlib import Path
from typing import Tuple
from .schemas import AssetType, ClassifiedAsset


def _is_ecg_image_name(filename: str) -> bool:
    lower_name = Path(filename).name.lower()
    return any(keyword in lower_name for keyword in ("ecg", "心电图", "cardio", "lead"))


def classify_asset(filename: str, content_type: str | None) -> str:
    """Classify a file into a simple kind string for the health pipeline."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "report_pdf"
    if suffix in {".dat", ".hea"}:
        return "ecg_signal"
    if suffix in {".png", ".jpg", ".jpeg"}:
        if _is_ecg_image_name(filename):
            return "ecg_image"
        return "report_image"
    raise ValueError(f"Unsupported upload: {filename}")


class HealthAssetClassifier:
    # ECG related keywords in filenames
    ECG_KEYWORDS = {"ecg", "心电图", "heart", "cardio"}

    # Supported extensions mapped to base types
    EXTENSION_MAP = {
        ".pdf": AssetType.HEALTH_REPORT_PDF,
        ".txt": AssetType.HEALTH_REPORT_TEXT,
        ".dat": AssetType.ECG_SIGNAL_DAT,
        ".hea": AssetType.ECG_SIGNAL_HEA,
        ".jpg": AssetType.HEALTH_REPORT_IMAGE,
        ".jpeg": AssetType.HEALTH_REPORT_IMAGE,
        ".png": AssetType.HEALTH_REPORT_IMAGE,
    }

    def classify(self, filename: str, content_type: str) -> AssetType:
        """Classify a file into appropriate AssetType"""
        path = Path(filename)
        suffix = path.suffix.lower()

        if suffix not in self.EXTENSION_MAP:
            raise ValueError(f"Unsupported file type: {suffix}")

        base_type = self.EXTENSION_MAP[suffix]

        # Check if image is ECG image based on filename keywords
        if base_type == AssetType.HEALTH_REPORT_IMAGE and _is_ecg_image_name(filename):
            return AssetType.ECG_IMAGE

        return base_type
