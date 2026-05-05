from .db_models import Base, DiagnosisRecord
from .user import User
from .refresh_token import RefreshToken
from .chat import ChatMessage, ChatSession
from .rate_limit import RateLimitCounter
from .health import HealthAsset, HealthFinding, HealthJob

# Import submodules so their ORM classes register on Base.metadata.
# A single ``import app.models`` is sufficient for both ``init_db()``
# and Alembic's ``env.py`` — no more scattered model imports.

__all__ = [
    "Base",
    "DiagnosisRecord",
    "User",
    "RefreshToken",
    "ChatMessage",
    "ChatSession",
    "RateLimitCounter",
    "HealthAsset",
    "HealthFinding",
    "HealthJob",
]
