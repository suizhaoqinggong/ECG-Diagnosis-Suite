import asyncio
import io
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.chat import ChatMessage, ChatSession
from app.models.db_models import Base
from app.models.health import HealthJob
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.user import User
from app.services.health_pipeline.composer import compose_health_report
from app.services.health_pipeline.service import HealthPipelineService


def test_compose_health_report_promotes_highest_risk():
    report = compose_health_report(
        findings=[
            {
                "id": "f1",
                "sourceType": "lab",
                "title": "LDL 偏高",
                "summary": "低密度脂蛋白高于参考范围。",
                "severity": "medium",
                "actionHint": "recheck",
                "evidence": ["LDL 4.9 mmol/L"],
            },
            {
                "id": "f2",
                "sourceType": "ecg_ai",
                "title": "心电图异常",
                "summary": "AI 提示需要进一步门诊评估。",
                "severity": "high",
                "actionHint": "clinic_visit",
                "evidence": ["预测结果：传导障碍"],
            },
        ]
    )
    assert report["overallRisk"] == "high"
    assert report["summary"] == "AI 提示需要进一步门诊评估。"


class StubEcgAdapter:
    async def analyze_bundle(self, paths):
        return {"prediction": "正常", "confidence": 0.91}


@pytest.fixture
def health_session_factory(tmp_path):
    db_path = tmp_path / "health-service.sqlite"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    factory = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        yield factory
    finally:
        asyncio.run(async_engine.dispose())
        sync_engine.dispose()


def _run(coro):
    return asyncio.run(coro)


async def _create_user(
    session_factory,
    *,
    email: str,
) -> User:
    async with session_factory() as session:
        user = User(
            email=email,
            hashed_password="hash",
            display_name="Tester",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _create_chat_session(
    session_factory,
    *,
    user_id: int,
    title: str = "Health Review",
    session_id: str | None = None,
) -> ChatSession:
    async with session_factory() as session:
        chat_session = ChatSession(
            id=session_id or str(uuid4()),
            user_id=user_id,
            title=title,
        )
        session.add(chat_session)
        await session.commit()
        await session.refresh(chat_session)
        return chat_session


async def _create_health_job(
    session_factory,
    *,
    user_id: int | None,
    session_id: str | None,
    job_id: str | None = None,
    status: str = "queued",
    message: str = "Queued",
) -> HealthJob:
    async with session_factory() as session:
        job = HealthJob(
            id=job_id or str(uuid4()),
            user_id=user_id,
            session_id=session_id,
            status=status,
            message=message,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


def _make_upload(filename: str, content: bytes = b"sample") -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename=filename)


def test_get_job_rejects_anonymous_access_to_user_owned_job(health_session_factory):
    user = _run(_create_user(health_session_factory, email="owner@example.com"))
    job = _run(
        _create_health_job(
            health_session_factory,
            user_id=user.id,
            session_id=None,
            status="completed",
            message="Completed",
        )
    )
    service = HealthPipelineService(ecg_adapter=StubEcgAdapter(), vision_extractor=None)

    with patch("app.services.health_pipeline.service.AsyncSessionLocal", health_session_factory):
        with pytest.raises(HTTPException) as exc_info:
            _run(service.get_job(job.id, None))

    assert exc_info.value.status_code == 404


def test_create_job_drops_anonymous_local_session_reference(health_session_factory, tmp_path):
    service = HealthPipelineService(ecg_adapter=StubEcgAdapter(), vision_extractor=None)
    service.process_job = AsyncMock(return_value=None)

    with (
        patch("app.services.health_pipeline.service.AsyncSessionLocal", health_session_factory),
        patch.object(
            settings,
            "UPLOAD_DIR",
            str(tmp_path / "uploads"),
        ),
    ):
        job = _run(
            service.create_job(
                files=[_make_upload("report.pdf", b"%PDF-1.4")],
                note=None,
                user_id=None,
                session_id="guest-only-session",
            )
        )

    async def _assertions():
        async with health_session_factory() as session:
            persisted_job = await session.get(HealthJob, job.id)
            persisted_message = await session.get(ChatMessage, job.id)
            assert persisted_job is not None
            assert persisted_job.session_id is None
            assert persisted_message is None

    _run(_assertions())


def test_create_job_rejects_session_not_owned_by_user(health_session_factory, tmp_path):
    owner = _run(_create_user(health_session_factory, email="owner@example.com"))
    other_user = _run(_create_user(health_session_factory, email="other@example.com"))
    other_session = _run(
        _create_chat_session(health_session_factory, user_id=other_user.id)
    )
    upload_root = tmp_path / "uploads"
    service = HealthPipelineService(ecg_adapter=StubEcgAdapter(), vision_extractor=None)
    service.process_job = AsyncMock(return_value=None)

    with (
        patch("app.services.health_pipeline.service.AsyncSessionLocal", health_session_factory),
        patch.object(
            settings,
            "UPLOAD_DIR",
            str(upload_root),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            _run(
                service.create_job(
                    files=[_make_upload("report.pdf")],
                    note=None,
                    user_id=owner.id,
                    session_id=other_session.id,
                )
            )

    assert exc_info.value.status_code == 404
    assert not upload_root.exists()


def test_create_job_cleans_up_saved_files_when_later_file_is_invalid(
    health_session_factory,
    tmp_path,
):
    upload_root = tmp_path / "uploads"
    service = HealthPipelineService(ecg_adapter=StubEcgAdapter(), vision_extractor=None)
    service.process_job = AsyncMock(return_value=None)

    with (
        patch("app.services.health_pipeline.service.AsyncSessionLocal", health_session_factory),
        patch.object(
            settings,
            "UPLOAD_DIR",
            str(upload_root),
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            _run(
                service.create_job(
                    files=[
                        _make_upload("report.pdf", b"%PDF-1.4"),
                        _make_upload("malware.exe", b"MZ"),
                    ],
                    note=None,
                    user_id=None,
                    session_id=None,
                )
            )

    assert exc_info.value.status_code == 400
    assert not any(path.is_file() for path in upload_root.rglob("*"))


def test_create_job_persists_pending_chat_message_for_owned_session(
    health_session_factory,
    tmp_path,
):
    user = _run(_create_user(health_session_factory, email="owner@example.com"))
    chat_session = _run(_create_chat_session(health_session_factory, user_id=user.id))
    service = HealthPipelineService(ecg_adapter=StubEcgAdapter(), vision_extractor=None)
    service.process_job = AsyncMock(return_value=None)

    with (
        patch("app.services.health_pipeline.service.AsyncSessionLocal", health_session_factory),
        patch.object(
            settings,
            "UPLOAD_DIR",
            str(tmp_path / "uploads"),
        ),
    ):
        job = _run(
            service.create_job(
                files=[_make_upload("report.pdf", b"%PDF-1.4")],
                note="LDL 高",
                user_id=user.id,
                session_id=chat_session.id,
            )
        )

    async def _assertions():
        async with health_session_factory() as session:
            message = await session.get(ChatMessage, job.id)
            assert message is not None
            assert message.session_id == chat_session.id
            assert message.status == "pending"
            assert message.type == "health_report"
            assert message.content == "分析中..."

    _run(_assertions())


def test_process_job_updates_persisted_chat_message_on_completion(
    health_session_factory,
):
    user = _run(_create_user(health_session_factory, email="owner@example.com"))
    chat_session = _run(_create_chat_session(health_session_factory, user_id=user.id))
    job = _run(
        _create_health_job(
            health_session_factory,
            user_id=user.id,
            session_id=chat_session.id,
            status="queued",
            message="Queued",
        )
    )

    previous_updated_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    async def _seed_message():
        async with health_session_factory() as session:
            persisted_session = await session.get(ChatSession, chat_session.id)
            persisted_session.updated_at = previous_updated_at
            session.add(
                ChatMessage(
                    id=job.id,
                    session_id=chat_session.id,
                    role="assistant",
                    type="health_report",
                    title="健康分析报告",
                    content="分析中...",
                    status="pending",
                )
            )
            await session.commit()

    _run(_seed_message())

    service = HealthPipelineService(ecg_adapter=StubEcgAdapter(), vision_extractor=None)
    service._extract_raw_items = AsyncMock(
        return_value=[{"source_type": "lab", "text": "LDL 4.9 mmol/L"}]
    )
    service._analyze_ecg_assets = AsyncMock(
        return_value={"prediction": "传导障碍", "confidence": 0.88}
    )

    with patch("app.services.health_pipeline.service.AsyncSessionLocal", health_session_factory):
        _run(service.process_job(job.id, note="需要结合症状判断"))

    async def _assertions():
        async with health_session_factory() as session:
            persisted_job = await session.get(HealthJob, job.id)
            persisted_message = await session.get(ChatMessage, job.id)
            persisted_session = await session.get(ChatSession, chat_session.id)

            assert persisted_job is not None
            assert persisted_job.status == "completed"
            assert persisted_job.result_payload is not None
            assert persisted_job.result_payload["jobId"] == job.id

            assert persisted_message is not None
            assert persisted_message.status == "completed"
            assert persisted_message.content == "分析完成"
            assert persisted_message.result == persisted_job.result_payload

            assert persisted_session is not None
            updated_at = persisted_session.updated_at
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            assert updated_at > previous_updated_at

    _run(_assertions())


def test_service_preserves_ecg_result_in_final_payload():
    service = HealthPipelineService(ecg_adapter=StubEcgAdapter())
    payload = asyncio.run(service._build_completed_payload(
        job_id="job-1",
        findings=[{
            "id": "f1",
            "sourceType": "lab",
            "title": "LDL 偏高",
            "summary": "低密度脂蛋白高于参考范围。",
            "severity": "medium",
            "actionHint": "recheck",
            "evidence": ["LDL 4.9 mmol/L"],
        }],
        ecg_result={"prediction": "正常", "confidence": 0.91},
    ))
    assert payload["jobId"] == "job-1"
    assert payload["ecgResult"]["prediction"] == "正常"
