from enum import Enum
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

class AssetType(str, Enum):
    HEALTH_REPORT_PDF = "health_report_pdf"
    HEALTH_REPORT_IMAGE = "health_report_image"
    HEALTH_REPORT_TEXT = "health_report_text"
    ECG_IMAGE = "ecg_image"
    ECG_SIGNAL_DAT = "ecg_signal_dat"
    ECG_SIGNAL_HEA = "ecg_signal_hea"

class ClassifiedAsset(BaseModel):
    file_path: Path
    file_name: str
    content_type: str
    asset_type: AssetType
    confidence: float = 1.0

class ExtractedText(BaseModel):
    text: str
    source_file: Path
    extraction_method: str
    confidence: Optional[float] = None
