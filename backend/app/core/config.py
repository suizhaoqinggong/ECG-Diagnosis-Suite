"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "ECG Diagnosis Suite"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-this"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database settings
    DATABASE_URL: str = "sqlite+aiosqlite:///./ecg_db.sqlite"

    # File upload settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "./data/uploads"
    ALLOWED_EXTENSIONS: List[str] = [".png", ".jpg", ".jpeg"]

    # Model settings
    MODEL_PATH: str = "./models/weights/ecg_model.pth"
    ONNX_MODEL_PATH: str = "./models/weights/ecg_model.onnx"
    DEVICE: str = "cpu"
    CONFIDENCE_THRESHOLD: float = 0.7

    # Report settings
    REPORT_OUTPUT_DIR: str = "./data/reports"

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
