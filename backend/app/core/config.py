"""
Application configuration
"""
import logging
import warnings
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)
_BACKEND_DIR = Path(__file__).resolve().parents[2]

load_dotenv(_BACKEND_DIR / ".env", override=False)
load_dotenv(_BACKEND_DIR / ".env.local", override=True)


class Settings(BaseSettings):
    _DEFAULT_SECRET_KEY: str = "your-secret-key-change-this"

    # App settings
    APP_NAME: str = "ECG Diagnosis Suite"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    DB_ECHO: bool = False
    SECRET_KEY: str = _DEFAULT_SECRET_KEY
    ENVIRONMENT: str = "development"  # "development" or "production"
    API_DOCS_ENABLED: bool = True
    RATE_LIMIT_BACKEND: str = "auto"  # "auto", "memory", or "database"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "testserver",
    ]

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
    MODEL_TEMPERATURE: float = Field(default=0.5, gt=0, description="温度缩放参数，必须>0")
    MODEL_NORMAL_BIAS: float = Field(default=1.8, ge=0, description="NORM类logit偏置补偿，必须>=0")

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
        "http://localhost:5174",
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
    def environment_name(self) -> str:
        return self.ENVIRONMENT.strip().lower()

    @property
    def is_production(self) -> bool:
        return self.environment_name == "production"

    @property
    def effective_rate_limit_backend(self) -> str:
        backend = self.RATE_LIMIT_BACKEND.strip().lower()
        if backend == "auto":
            return "database" if self.is_production else "memory"
        return backend

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

    @model_validator(mode="after")
    def _validate_production_settings(self):
        env = self.environment_name
        if env == "production":
            if self.SECRET_KEY == self._DEFAULT_SECRET_KEY:
                raise ValueError(
                    "SECRET_KEY must be overridden in production. "
                    "Set the SECRET_KEY environment variable to a strong random value."
                )
            if self.DEBUG:
                warnings.warn(
                    "DEBUG=True in production environment. "
                    "This should be disabled for security.",
                    stacklevel=2,
                )
        else:
            if self.SECRET_KEY == self._DEFAULT_SECRET_KEY:
                logger.warning(
                    "Using default SECRET_KEY in development mode. "
                    "Set SECRET_KEY environment variable for production."
                )
        if self.effective_rate_limit_backend not in {"memory", "database"}:
            raise ValueError(
                "RATE_LIMIT_BACKEND must resolve to 'memory' or 'database'."
            )
        return self

    def ensure_runtime_dirs(self) -> None:
        self.upload_dir_path.mkdir(parents=True, exist_ok=True)
        self.report_output_dir_path.mkdir(parents=True, exist_ok=True)

    model_config = ConfigDict(
        case_sensitive=True,
    )


settings = Settings()
