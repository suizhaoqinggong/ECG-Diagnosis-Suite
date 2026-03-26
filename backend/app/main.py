"""
FastAPI main application
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api import diagnosis, conduction_disorder

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.ensure_runtime_dirs()
    try:
        await init_db()
    except Exception as exc:
        logger.warning("Database initialization skipped: %s", exc)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered ECG diagnosis system",
    lifespan=lifespan,
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
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
