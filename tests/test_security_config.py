"""
Protective tests for security configuration baseline.

These tests verify the P1-6 security tightening:
SECRET_KEY enforcement, CORS configuration, security headers, origin validation.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.config import Settings, settings
from app.main import app


# ===========================================================================
# SECRET_KEY
# ===========================================================================


class TestSecretKey:
    """Tests for SECRET_KEY configuration behavior."""

    def test_default_secret_key_is_predictable(self):
        """The default SECRET_KEY is a known placeholder — not production-safe."""
        s = Settings(SECRET_KEY="your-secret-key-change-this")
        assert s.SECRET_KEY == "your-secret-key-change-this"

    def test_secret_key_can_be_overridden(self):
        s = Settings(SECRET_KEY="a-real-secret-from-env")
        assert s.SECRET_KEY == "a-real-secret-from-env"

    def test_current_settings_default_key(self):
        """Current settings instance uses the default placeholder."""
        assert settings.SECRET_KEY == "your-secret-key-change-this"

    def test_is_default_key_detection(self):
        """We can detect when the default key is in use."""
        default = "your-secret-key-change-this"
        s1 = Settings(SECRET_KEY=default)
        s2 = Settings(SECRET_KEY="overridden-key")
        assert s1.SECRET_KEY == default
        assert s2.SECRET_KEY != default

    def test_production_mode_rejects_default_secret_key(self):
        """Production environment must not allow the default SECRET_KEY."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                SECRET_KEY="your-secret-key-change-this",
                ENVIRONMENT="production",
            )
        assert "SECRET_KEY must be overridden in production" in str(exc_info.value)

    def test_production_allows_custom_secret_key(self):
        """Production environment accepts a custom SECRET_KEY."""
        s = Settings(
            SECRET_KEY="a-real-secret-from-env",
            ENVIRONMENT="production",
        )
        assert s.SECRET_KEY == "a-real-secret-from-env"

    def test_development_allows_default_secret_key(self):
        """Development environment allows the default SECRET_KEY (with warning)."""
        s = Settings(
            SECRET_KEY="your-secret-key-change-this",
            ENVIRONMENT="development",
        )
        assert s.SECRET_KEY == "your-secret-key-change-this"


# ===========================================================================
# DEBUG mode
# ===========================================================================


class TestDebugMode:
    """Tests for DEBUG configuration."""

    def test_default_is_debug_true(self):
        """Default is DEBUG=True, which is development-friendly."""
        s = Settings()
        assert s.DEBUG is True

    def test_debug_can_be_disabled(self):
        s = Settings(DEBUG=False)
        assert s.DEBUG is False


# ===========================================================================
# ENVIRONMENT
# ===========================================================================


class TestEnvironment:
    """Tests for ENVIRONMENT configuration."""

    def test_default_environment_is_development(self):
        s = Settings()
        assert s.ENVIRONMENT == "development"

    def test_environment_can_be_set_to_production(self):
        s = Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a-real-secret-from-env",
        )
        assert s.ENVIRONMENT == "production"


# ===========================================================================
# CORS configuration
# ===========================================================================


class TestCORSConfiguration:
    """Tests for CORS middleware configuration values."""

    def test_default_cors_origins_are_localhost_only(self):
        """Default CORS origins only allow local development servers."""
        s = Settings()
        for origin in s.CORS_ORIGINS:
            assert "localhost" in origin

    def test_cors_origins_can_be_overridden(self):
        s = Settings(CORS_ORIGINS=["https://example.com"])
        assert s.CORS_ORIGINS == ["https://example.com"]

    def test_cors_methods_are_explicit(self):
        """CORS allow_methods is an explicit list, not a wildcard."""
        from app.main import app

        cors_middleware = None
        for mw in app.user_middleware:
            if hasattr(mw.cls, "__name__") and "CORS" in mw.cls.__name__:
                cors_middleware = mw
                break
        assert cors_middleware is not None
        # The kwargs should contain explicit methods, not ["*"]
        methods = cors_middleware.kwargs.get("allow_methods", [])
        assert methods != ["*"]
        assert isinstance(methods, list)
        assert "GET" in methods
        assert "POST" in methods
        assert "OPTIONS" in methods

    def test_cors_headers_are_explicit(self):
        """CORS allow_headers is an explicit list, not a wildcard."""
        from app.main import app

        cors_middleware = None
        for mw in app.user_middleware:
            if hasattr(mw.cls, "__name__") and "CORS" in mw.cls.__name__:
                cors_middleware = mw
                break
        assert cors_middleware is not None
        headers = cors_middleware.kwargs.get("allow_headers", [])
        assert headers != ["*"]
        assert isinstance(headers, list)
        assert "Authorization" in headers
        assert "Content-Type" in headers


# ===========================================================================
# Security headers
# ===========================================================================


class TestSecurityHeaders:
    """Tests for presence of security response headers."""

    @pytest.fixture
    def client(self):
        return TestClient(app, raise_server_exceptions=False)

    def test_security_headers_present_on_responses(self, client):
        """Security headers are now set on all responses."""
        response = client.get("/health")
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert response.headers.get("x-frame-options") == "DENY"
        assert (
            response.headers.get("referrer-policy")
            == "strict-origin-when-cross-origin"
        )

    def test_hsts_not_set_in_debug_mode(self, client):
        """HSTS header is not set when DEBUG=True (development mode)."""
        response = client.get("/health")
        assert "strict-transport-security" not in {
            k.lower() for k in response.headers
        }


# ===========================================================================
# Cookie security
# ===========================================================================


class TestCookieSecurity:
    """Tests for cookie security settings in auth routes."""

    def test_cookie_settings_reflect_debug_mode(self):
        """Cookie secure flag is tied to DEBUG: secure when not DEBUG."""
        from app.api.auth import _set_refresh_cookie
        from starlette.responses import Response

        # When DEBUG=True (default), secure=False
        with patch.object(settings, "DEBUG", True):
            response = Response()
            _set_refresh_cookie(response, "test-token")
            cookie_header = response.headers.get("set-cookie", "")
            # In debug mode, Secure should NOT be set
            # starlette may not include it when secure=False

        # When DEBUG=False, secure=True
        with patch.object(settings, "DEBUG", False):
            response = Response()
            _set_refresh_cookie(response, "test-token")
            cookie_header = response.headers.get("set-cookie", "")
            assert "secure" in cookie_header.lower()

    def test_cookie_is_httponly(self):
        from app.api.auth import _set_refresh_cookie
        from starlette.responses import Response

        response = Response()
        _set_refresh_cookie(response, "test-token")
        cookie_header = response.headers.get("set-cookie", "")
        assert "httponly" in cookie_header.lower()

    def test_cookie_is_samesite_lax(self):
        from app.api.auth import _set_refresh_cookie
        from starlette.responses import Response

        response = Response()
        _set_refresh_cookie(response, "test-token")
        cookie_header = response.headers.get("set-cookie", "")
        assert "samesite=lax" in cookie_header.lower()

    def test_cookie_path_scoped_to_auth(self):
        from app.api.auth import _set_refresh_cookie
        from starlette.responses import Response

        response = Response()
        _set_refresh_cookie(response, "test-token")
        cookie_header = response.headers.get("set-cookie", "")
        assert "path=/api/auth" in cookie_header.lower()


# ===========================================================================
# Origin validation
# ===========================================================================


class TestOriginValidation:
    """Tests for _validate_origin CSRF check."""

    def test_allows_no_origin(self):
        """Requests without Origin header are allowed (same-origin)."""
        from app.api.auth import _validate_origin
        from fastapi import Request

        # Minimal request mock with no origin
        scope = {"type": "http", "headers": []}
        request = Request(scope)
        # Should not raise
        _validate_origin(request)

    def test_allows_matching_origin(self):
        from app.api.auth import _validate_origin
        from fastapi import Request

        scope = {
            "type": "http",
            "headers": [
                (b"origin", b"http://localhost:5173"),
            ],
        }
        request = Request(scope)
        # Should not raise
        _validate_origin(request)

    def test_rejects_unknown_origin(self):
        from app.api.auth import _validate_origin
        from fastapi import Request, HTTPException

        scope = {
            "type": "http",
            "headers": [
                (b"origin", b"https://evil.com"),
            ],
        }
        request = Request(scope)
        with pytest.raises(HTTPException) as exc_info:
            _validate_origin(request)
        assert exc_info.value.status_code == 403

    def test_rejects_spoofed_origin_with_subdomain(self):
        """Spoofed origins like localhost:5173.evil.com are now properly rejected."""
        from app.api.auth import _validate_origin
        from fastapi import Request, HTTPException

        # This SHOULD be rejected — proper URL parsing prevents the startswith bypass
        scope = {
            "type": "http",
            "headers": [
                (b"origin", b"http://localhost:5173.evil.com"),
            ],
        }
        request = Request(scope)
        with pytest.raises(HTTPException) as exc_info:
            _validate_origin(request)
        assert exc_info.value.status_code == 403

    def test_rejects_wrong_scheme(self):
        """Origins with wrong scheme are rejected."""
        from app.api.auth import _validate_origin
        from fastapi import Request, HTTPException

        scope = {
            "type": "http",
            "headers": [
                (b"origin", b"https://localhost:5173"),
            ],
        }
        request = Request(scope)
        with pytest.raises(HTTPException) as exc_info:
            _validate_origin(request)
        assert exc_info.value.status_code == 403

    def test_rejects_wrong_port(self):
        """Origins with wrong port are rejected."""
        from app.api.auth import _validate_origin
        from fastapi import Request, HTTPException

        scope = {
            "type": "http",
            "headers": [
                (b"origin", b"http://localhost:9999"),
            ],
        }
        request = Request(scope)
        with pytest.raises(HTTPException) as exc_info:
            _validate_origin(request)
        assert exc_info.value.status_code == 403

    def test_allows_all_configured_origins(self):
        """All origins in CORS_ORIGINS are accepted."""
        from app.api.auth import _validate_origin
        from fastapi import Request

        for allowed_origin in settings.CORS_ORIGINS:
            scope = {
                "type": "http",
                "headers": [
                    (b"origin", allowed_origin.encode()),
                ],
            }
            request = Request(scope)
            # Should not raise for any configured origin
            _validate_origin(request)
