"""
FastAPI main application
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import settings
from app.core.database import get_database_status, init_db, mark_db_unavailable
from app.api import auth, chat, diagnosis, conduction_disorder

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.ensure_runtime_dirs()
    try:
        await init_db()
    except Exception as exc:
        mark_db_unavailable(exc)
        logger.warning("Database initialization skipped: %s", exc)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered ECG diagnosis system",
    lifespan=lifespan,
    docs_url="/docs" if settings.API_DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.API_DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.API_DOCS_ENABLED else None,
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS or ["*"],
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(diagnosis.router, prefix="/api", tags=["diagnosis"])
app.include_router(conduction_disorder.router, prefix="/api", tags=["conduction-disorder"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to ECG Diagnosis Suite API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    db_status = get_database_status()
    status_value = "healthy" if db_status.ready else "degraded"
    return {
        "status": status_value,
        "database": {
            "ready": db_status.ready,
            "error": db_status.error,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
