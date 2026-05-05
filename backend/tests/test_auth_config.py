from app.core.config import Settings


def test_loopback_cors_origins_include_localhost_and_127_variants():
    settings = Settings(
        CORS_ORIGINS=[
            "http://localhost:5173",
            "http://127.0.0.1:8000",
        ]
    )

    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert "http://127.0.0.1:5173" in settings.CORS_ORIGINS
    assert "http://127.0.0.1:8000" in settings.CORS_ORIGINS
    assert "http://localhost:8000" in settings.CORS_ORIGINS
