from __future__ import annotations

from pathlib import Path
from typing import Tuple
from .schemas import AssetType, ClassifiedAsset


def classify_asset(filename: str, content_type: str | None) -> str:
    """Classify a file into a simple kind string for the health pipeline."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "report_pdf"
    if suffix in {".dat", ".hea"}:
        return "ecg_signal"
    if suffix in {".png", ".jpg", ".jpeg"}:
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
        if base_type == AssetType.HEALTH_REPORT_IMAGE:
            file_name_lower = path.name.lower()
            for keyword in self.ECG_KEYWORDS:
                if keyword in file_name_lower:
                    return AssetType.ECG_IMAGE

        return base_type
