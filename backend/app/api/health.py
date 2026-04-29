from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel

from app.core.auth_dependencies import get_optional_user
from app.models.user import User
from app.services.health_pipeline.service import HealthPipelineService

router = APIRouter(prefix="/health", tags=["health"])


class HealthJobResponse(BaseModel):
    id: str
    status: str
    message: str
    result: dict | None = None
    error: str | None = None


@router.post("/jobs")
async def create_health_job(
    files: list[UploadFile] = File(...),
    note: str | None = Form(default=None),
    session_id: str | None = Form(default=None),
    current_user: Annotated[User | None, Depends(get_optional_user)] = None,
):
    service = HealthPipelineService()
    job = await service.create_job(
        files=files,
        note=note,
        user_id=current_user.id if current_user else None,
        session_id=session_id,
    )
    return HealthJobResponse(id=job.id, status=job.status, message=job.message)


@router.get("/jobs/{job_id}")
async def get_health_job(
    job_id: str,
    current_user: Annotated[User | None, Depends(get_optional_user)] = None,
):
    service = HealthPipelineService()
    job = await service.get_job(job_id, current_user.id if current_user else None)
    return HealthJobResponse(
        id=job.id,
        status=job.status,
        message=job.message,
        result=job.result_payload,
        error=job.error_detail,
    )
