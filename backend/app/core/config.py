"""
Application configuration
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Optional


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
    UPLOAD_DIR: str = "data/uploads"
    ALLOWED_EXTENSIONS: List[str] = [".png", ".jpg", ".jpeg", ".dat", ".hea"]

    # Image processing limits
    IMAGE_MAX_PIXELS: int = 178_956_970  # ~178MP, Pillow default threshold
    IMAGE_MAX_DIMENSION: int = 16000  # Max single dimension (width or height)
    IMAGE_PROCESSING_MAX_DIMENSION: int = 4096  # Downsample threshold for large images

    # Model settings
    MODEL_CHECKPOINT_PATH: Optional[str] = None
    DEVICE: str = "cpu"
    CONFIDENCE_THRESHOLD: float = 0.7

    # Report settings
    REPORT_OUTPUT_DIR: str = "data/reports"
    LLM_REPORT_ENABLED: bool = False
    LLM_REPORT_PROVIDER: str = "openai"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_REPORT_MODEL: str = "gpt-4o-mini"
    OPENAI_TIMEOUT_SECONDS: int = 30
    ANTHROPIC_COMPAT_API_KEY: Optional[str] = None
    ANTHROPIC_COMPAT_BASE_URL: str = "https://open.bigmodel.cn/api/anthropic"
    ANTHROPIC_COMPAT_MODEL: str = "glm-5"
    ANTHROPIC_COMPAT_MAX_TOKENS: int = 2048
    ANTHROPIC_COMPAT_TIMEOUT_SECONDS: int = 30

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @property
    def backend_dir(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def project_root(self) -> Path:
        return self.backend_dir.parent

    def resolve_backend_path(self, path_value: str) -> Path:
        path = Path(path_value).expanduser()
        return path if path.is_absolute() else self.backend_dir / path

    def resolve_project_path(self, path_value: str) -> Path:
        path = Path(path_value).expanduser()
        return path if path.is_absolute() else self.project_root / path

    @property
    def upload_dir_path(self) -> Path:
        return self.resolve_backend_path(self.UPLOAD_DIR)

    @property
    def report_output_dir_path(self) -> Path:
        return self.resolve_backend_path(self.REPORT_OUTPUT_DIR)

    def get_model_checkpoint_path(self) -> Optional[Path]:
        candidates: list[Path] = []

        if self.MODEL_CHECKPOINT_PATH:
            candidates.extend(
                [
                    self.resolve_project_path(self.MODEL_CHECKPOINT_PATH),
                    self.resolve_backend_path(self.MODEL_CHECKPOINT_PATH),
                ]
            )

        candidates.extend(
            [
                self.backend_dir / "models" / "checkpoints" / "best.ckpt",
                self.backend_dir / "models" / "weights" / "best.ckpt",
                self.project_root / "models" / "checkpoints" / "best.ckpt",
                self.project_root / "models" / "weights" / "best.ckpt",
            ]
        )

        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if resolved.exists():
                return resolved

        return None

    def ensure_runtime_dirs(self) -> None:
        self.upload_dir_path.mkdir(parents=True, exist_ok=True)
        self.report_output_dir_path.mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        case_sensitive = True


settings = Settings()
