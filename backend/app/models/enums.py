from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageType(str, Enum):
    INTRO = "intro"
    PROMPT = "prompt"
    GUIDANCE = "guidance"
    DIAGNOSIS = "diagnosis"
    HEALTH_REPORT = "health_report"


class MessageStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    ERROR = "error"


class HealthReportType(str, Enum):
    ECG_DIAGNOSIS = "ecg_diagnosis"
    LAB_RESULT = "lab_result"
    MEDICAL_RECORD = "medical_record"
    PRESCRIPTION = "prescription"


class AttachmentCategory(str, Enum):
    ECG_IMAGE = "ecg_image"
    ECG_SIGNAL = "ecg_signal"
    PDF_REPORT = "pdf_report"
    LAB_FILE = "lab_file"
    OTHER = "other"
