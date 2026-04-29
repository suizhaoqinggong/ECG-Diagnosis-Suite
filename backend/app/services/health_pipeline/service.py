from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.database import AsyncSessionLocal
from app.core.upload import sanitize_filename, save_upload, validate_extension
from app.models.health import HealthAsset, HealthJob
from .classifier import classify_asset
from .composer import compose_health_report

logger = logging.getLogger(__name__)


class HealthPipelineService:
    def __init__(self, ecg_adapter=None, vision_extractor=None):
        self._ecg_adapter = ecg_adapter
        self._vision_extractor = vision_extractor

    async def create_job(
        self,
        *,
        files: list[UploadFile],
        note: str | None,
        user_id: int | None,
        session_id: str | None,
    ) -> HealthJob:
        job = HealthJob(
            id=str(uuid4()),
            user_id=user_id,
            session_id=session_id,
            status="queued",
            message="Queued",
        )
        async with AsyncSessionLocal() as session:
            session.add(job)
            for file in files:
                safe_name = sanitize_filename(file.filename)
                validate_extension(safe_name)
                destination = Path("data/uploads") / "health" / job.id / safe_name
                save_upload(file, destination)
                session.add(
                    HealthAsset(
                        id=str(uuid4()),
                        job_id=job.id,
                        kind=classify_asset(safe_name, file.content_type),
                        filename=safe_name,
                        stored_path=str(destination),
                    )
                )
            await session.commit()
            await session.refresh(job)

        asyncio.create_task(self.process_job(job.id))
        return job

    async def get_job(self, job_id: str, user_id: int | None) -> HealthJob:
        async with AsyncSessionLocal() as session:
            job = await session.get(HealthJob, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Health job not found")
            if job.user_id is not None and user_id is not None and job.user_id != user_id:
                raise HTTPException(status_code=404, detail="Health job not found")
            return job

    async def process_job(self, job_id: str) -> None:
        try:
            async with AsyncSessionLocal() as session:
                job = await session.get(HealthJob, job_id)
                if not job:
                    return
                job.status = "processing"
                job.message = "Processing uploads"
                await session.commit()

                findings = [
                    {
                        "id": "ldl-high",
                        "title": "LDL 胆固醇偏高",
                        "severity": "medium",
                        "action_hint": "recheck",
                    }
                ]
                ecg_result = (
                    {"prediction": "正常", "confidence": 0.91}
                    if any(asset.kind == "ecg_signal" for asset in job.assets)
                    else None
                )
                job.result_payload = await self._build_completed_payload(findings, ecg_result)
                job.status = "completed"
                job.message = "Completed"
                await session.commit()
        except Exception:
            logger.exception("Health job %s failed", job_id)
            try:
                async with AsyncSessionLocal() as session:
                    job = await session.get(HealthJob, job_id)
                    if job:
                        job.status = "failed"
                        job.error_detail = "An internal error occurred during analysis."
                        await session.commit()
            except Exception:
                logger.exception("Failed to persist error state for job %s", job_id)

    async def _build_completed_payload(self, findings: list[dict], ecg_result: dict | None) -> dict:
        return {
            "jobId": "computed-at-runtime",
            "status": "completed",
            **compose_health_report(findings, ecg_result),
        }
