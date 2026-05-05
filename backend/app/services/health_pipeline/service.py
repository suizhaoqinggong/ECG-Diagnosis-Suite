from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.upload import sanitize_filename, save_upload, validate_extension
from app.models.chat import ChatMessage, ChatSession
from app.models.enums import MessageRole, MessageStatus, MessageType
from app.models.health import HealthAsset, HealthFinding, HealthJob
from app.services.diagnosis_service import DiagnosisService, get_model_service
from app.services.ecg_dat_loader import ECGDataLoader
from ml.image_decoder import safe_decode_image
from .classifier import classify_asset
from .composer import compose_health_report
from .extractors import (
    build_default_vision_extractor,
    extract_pdf_text,
    extract_report_image_text,
)
from .rules import build_ecg_finding, normalize_findings

logger = logging.getLogger(__name__)
_DIAGNOSIS_SEMAPHORE = asyncio.Semaphore(4)


class HealthPipelineService:
    def __init__(self, ecg_adapter=None, vision_extractor=None):
        self._ecg_adapter = ecg_adapter or DiagnosisService(
            get_model_service_fn=get_model_service,
            ecg_loader_cls=ECGDataLoader,
            decode_image_fn=safe_decode_image,
            semaphore=_DIAGNOSIS_SEMAPHORE,
        )
        self._vision_extractor = (
            vision_extractor
            if vision_extractor is not None
            else build_default_vision_extractor()
        )

    async def _resolve_owned_session_id(
        self,
        session,
        *,
        session_id: str | None,
        user_id: int | None,
    ) -> str | None:
        if not session_id or user_id is None:
            return None

        result = await session.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == user_id)
        )
        chat_session = result.scalar_one_or_none()
        if chat_session is None:
            raise HTTPException(status_code=404, detail="Chat session not found")

        return chat_session.id

    async def _upsert_job_chat_message(
        self,
        session,
        job: HealthJob,
        *,
        status: str,
        content: str,
        result_payload: dict | None = None,
    ) -> None:
        if job.user_id is None or not job.session_id:
            return

        chat_session = await session.get(ChatSession, job.session_id)
        if chat_session is None or chat_session.user_id != job.user_id:
            return

        message = await session.get(ChatMessage, job.id)
        if message is None:
            message = ChatMessage(
                id=job.id,
                session_id=chat_session.id,
                role=MessageRole.ASSISTANT.value,
                type=MessageType.HEALTH_REPORT.value,
                title="健康分析报告",
                content=content,
                result=result_payload,
                result_schema_version=1 if result_payload else None,
                status=status,
            )
            session.add(message)
        else:
            message.role = MessageRole.ASSISTANT.value
            message.type = MessageType.HEALTH_REPORT.value
            message.title = "健康分析报告"
            message.content = content
            message.result = result_payload
            message.result_schema_version = 1 if result_payload else None
            message.status = status

        chat_session.updated_at = datetime.now(timezone.utc)

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
            session_id=None,
            status="queued",
            message="Queued",
        )
        upload_dir = settings.upload_dir_path / "health" / job.id
        async with AsyncSessionLocal() as session:
            try:
                job.session_id = await self._resolve_owned_session_id(
                    session,
                    session_id=session_id,
                    user_id=user_id,
                )
                session.add(job)

                for file in files:
                    safe_name = sanitize_filename(file.filename)
                    validate_extension(safe_name)
                    destination = (upload_dir / safe_name).resolve()
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

                await self._upsert_job_chat_message(
                    session,
                    job,
                    status=MessageStatus.PENDING.value,
                    content="分析中...",
                )
                await session.commit()
                await session.refresh(job)
            except Exception:
                await session.rollback()
                shutil.rmtree(upload_dir, ignore_errors=True)
                raise

        asyncio.create_task(self.process_job(job.id, note=note))
        return job

    async def get_job(self, job_id: str, user_id: int | None) -> HealthJob:
        async with AsyncSessionLocal() as session:
            job = await session.get(HealthJob, job_id)
            if not job:
                raise HTTPException(status_code=404, detail="Health job not found")
            if job.user_id is not None and (user_id is None or job.user_id != user_id):
                raise HTTPException(status_code=404, detail="Health job not found")
            return job

    async def process_job(self, job_id: str, note: str | None = None) -> None:
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(HealthJob)
                    .options(
                        selectinload(HealthJob.assets),
                        selectinload(HealthJob.findings),
                    )
                    .where(HealthJob.id == job_id)
                )
                job = result.scalar_one_or_none()
                if not job:
                    return
                job.status = "processing"
                job.message = "Processing uploads"
                job.error_detail = None
                await session.commit()

                raw_items = await self._extract_raw_items(job.assets, note=note)
                findings = normalize_findings(raw_items)
                ecg_result = await self._analyze_ecg_assets(job.assets, user_id=job.user_id)
                ecg_finding = build_ecg_finding(ecg_result)
                if ecg_finding:
                    findings.append(ecg_finding)

                for existing in list(job.findings):
                    await session.delete(existing)
                await session.flush()

                for finding in findings:
                    session.add(
                        HealthFinding(
                            id=str(uuid4()),
                            job_id=job.id,
                            source_type=finding["sourceType"],
                            title=finding["title"],
                            severity=finding["severity"],
                            action_hint=finding["actionHint"],
                            payload=finding,
                        )
                    )

                job.result_payload = await self._build_completed_payload(
                    job_id=job.id,
                    findings=findings,
                    ecg_result=ecg_result,
                )
                job.status = "completed"
                job.message = "Completed"
                await self._upsert_job_chat_message(
                    session,
                    job,
                    status=MessageStatus.COMPLETED.value,
                    content="分析完成",
                    result_payload=job.result_payload,
                )
                await session.commit()
        except Exception:
            logger.exception("Health job %s failed", job_id)
            try:
                async with AsyncSessionLocal() as session:
                    job = await session.get(HealthJob, job_id)
                    if job:
                        error_detail = "An internal error occurred during analysis."
                        job.status = "failed"
                        job.message = "Failed"
                        job.error_detail = error_detail
                        await self._upsert_job_chat_message(
                            session,
                            job,
                            status=MessageStatus.ERROR.value,
                            content=error_detail,
                            result_payload={"errorDetail": error_detail},
                        )
                        await session.commit()
            except Exception:
                logger.exception("Failed to persist error state for job %s", job_id)

    async def _extract_raw_items(
        self,
        assets: list[HealthAsset],
        *,
        note: str | None,
    ) -> list[dict[str, str]]:
        raw_items: list[dict[str, str]] = []

        if note and note.strip():
            raw_items.append(
                {
                    "source_type": "health_check_summary",
                    "text": note.strip(),
                }
            )

        for asset in assets:
            path = Path(asset.stored_path)
            text = ""
            source_type = "health_check_summary"

            if asset.kind == "report_pdf":
                text = extract_pdf_text(path)
                source_type = "lab"
            elif asset.kind == "report_image":
                text = await extract_report_image_text(path, self._vision_extractor)
                source_type = "health_check_summary"

            if text.strip():
                raw_items.append(
                    {
                        "source_type": source_type,
                        "text": text.strip(),
                    }
                )

        return raw_items

    async def _analyze_ecg_assets(
        self,
        assets: list[HealthAsset],
        *,
        user_id: int | None,
    ) -> dict | None:
        dat_asset = next(
            (
                asset
                for asset in assets
                if asset.kind == "ecg_signal" and asset.filename.lower().endswith(".dat")
            ),
            None,
        )
        if dat_asset:
            response = await self._ecg_adapter.diagnose_signal(
                dat_path=Path(dat_asset.stored_path),
                file_reference=dat_asset.filename,
                user_id=user_id,
            )
            return response.model_dump()

        image_asset = next((asset for asset in assets if asset.kind == "ecg_image"), None)
        if image_asset:
            with Path(image_asset.stored_path).open("rb") as handle:
                upload = UploadFile(filename=image_asset.filename, file=handle)
                response = await self._ecg_adapter.diagnose_image(
                    upload,
                    image_asset.filename,
                    user_id=user_id,
                )
            return response.model_dump()

        return None

    async def _build_completed_payload(
        self,
        *,
        job_id: str,
        findings: list[dict],
        ecg_result: dict | None,
    ) -> dict:
        return {
            "jobId": job_id,
            "status": "completed",
            **compose_health_report(findings, ecg_result),
        }
