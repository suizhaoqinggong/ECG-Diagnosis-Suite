import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_SALT_BYTES = 16
SCRYPT_KEY_BYTES = 32


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _hash_password_scrypt(password: str) -> str:
    salt = secrets.token_bytes(SCRYPT_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_KEY_BYTES,
    )
    return (
        f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}$"
        f"{_b64encode(salt)}${_b64encode(digest)}"
    )


def _verify_scrypt_password(password: str, hashed_password: str) -> bool:
    try:
        _, n_value, r_value, p_value, salt_value, digest_value = hashed_password.split("$", 5)
        expected = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_b64decode(salt_value),
            n=int(n_value),
            r=int(r_value),
            p=int(p_value),
            dklen=len(_b64decode(digest_value)),
        )
        return hmac.compare_digest(expected, _b64decode(digest_value))
    except Exception:
        return False


def _verify_legacy_bcrypt(password: str, hashed_password: str) -> bool:
    try:
        import bcrypt  # type: ignore

        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if hashed_password.startswith("scrypt$"):
        return _verify_scrypt_password(plain_password, hashed_password)
    if hashed_password.startswith("$2"):
        return _verify_legacy_bcrypt(plain_password, hashed_password)
    return False


def get_password_hash(password: str) -> str:
    return _hash_password_scrypt(password)


def create_access_token(subject: int) -> tuple[str, datetime]:
    """Create JWT access token. Returns (token, expiry)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode: dict[str, Any] = {"sub": str(subject), "exp": expire}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate JWT. Returns payload or None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_refresh_token() -> str:
    """Generate opaque random refresh token."""
    import secrets

    return secrets.token_urlsafe(32)
