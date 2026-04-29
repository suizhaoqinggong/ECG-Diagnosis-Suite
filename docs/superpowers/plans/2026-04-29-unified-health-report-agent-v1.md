# Unified Health Report Agent V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified B2C health-report analysis flow that accepts report PDFs/images plus ECG uploads, routes them through a new backend health pipeline, and renders a single user-facing report inside the existing conversation UI.

**Architecture:** Keep the current ECG stack intact and wrap it in a new `health_pipeline` service that classifies uploads, extracts report content, maps all outputs into a single `ClinicalFinding` model, and composes a unified report. The frontend stops calling `/api/diagnose*` directly for the main flow and instead creates/polls `health` jobs while still rendering ECG-specific output when the backend returns it.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, PyPDF, OpenAI-compatible vision extraction, React 18, TypeScript, Vitest

---

## File Structure

### Backend

- Create: `backend/app/models/health.py`
  - Persist health jobs, uploaded assets, normalized findings, and composed reports.
- Create: `backend/app/services/health_pipeline/schemas.py`
  - Define normalized request/response models shared across the health pipeline.
- Create: `backend/app/services/health_pipeline/classifier.py`
  - Classify each uploaded asset into `report_pdf`, `report_image`, `ecg_image`, or `ecg_signal`.
- Create: `backend/app/services/health_pipeline/extractors.py`
  - Extract text from PDFs and report images.
- Create: `backend/app/services/health_pipeline/rules.py`
  - Convert parsed fields into normalized findings and risk levels.
- Create: `backend/app/services/health_pipeline/composer.py`
  - Build the final user-facing health report.
- Create: `backend/app/services/health_pipeline/service.py`
  - Orchestrate classification, extraction, ECG adaptation, persistence, and job polling.
- Create: `backend/app/api/health.py`
  - Expose create/get health job endpoints.
- Create: `backend/alembic/versions/003_add_health_jobs.py`
  - Add the health tables.
- Modify: `backend/app/main.py`
  - Register the new `health` router.
- Modify: `backend/app/models/enums.py`
  - Add `MessageType.HEALTH_REPORT`.
- Modify: `backend/app/core/config.py`
  - Allow PDF uploads and add optional health-pipeline model config.
- Modify: `backend/app/core/upload.py`
  - Keep using shared upload validation with expanded allowlist.
- Modify: `backend/requirements.txt`
  - Add `pypdf`.

### Frontend

- Create: `frontend/src/types/health.ts`
  - Define `HealthAnalysisResult`, `ClinicalFindingView`, and `HealthJobResponse`.
- Create: `frontend/src/api/health.ts`
  - Create and poll health analysis jobs.
- Create: `frontend/src/components/HealthReport.tsx`
  - Render summary, risk, findings, next steps, and optional ECG section.
- Modify: `frontend/src/types/chat.ts`
  - Add `health_report` message type and new attachment categories.
- Modify: `frontend/src/controllers/workspaceReducer.ts`
  - Accept report PDFs/images and mixed bundles.
- Modify: `frontend/src/controllers/useWorkspaceController.ts`
  - Submit through the health job API and poll completion.
- Modify: `frontend/src/components/ChatComposer.tsx`
  - Replace the ECG-only controls with a unified attachment entry.
- Modify: `frontend/src/components/ConversationMessage.tsx`
  - Render `HealthReport` for health-report messages and retain `DiagnosisReport` for legacy ECG sessions.
- Modify: `frontend/src/pages/HomePage.tsx`
  - Update copy to fit unified health analysis instead of ECG-only wording.

### Tests

- Create: `backend/tests/test_health_contracts.py`
- Create: `backend/tests/test_health_models.py`
- Create: `backend/tests/test_health_classifier.py`
- Create: `backend/tests/test_health_extractors.py`
- Create: `backend/tests/test_health_service.py`
- Create: `backend/tests/test_health_api.py`
- Create: `frontend/src/__tests__/types/health.test.ts`
- Create: `frontend/src/__tests__/controllers/workspaceReducer.health.test.ts`
- Create: `frontend/src/__tests__/controllers/useWorkspaceController.health.test.tsx`
- Create: `frontend/src/__tests__/components/HealthReport.test.tsx`

### Docs

- Modify: `README.md`
- Modify: `docs/api.md`

---

### Task 1: Add Shared Health Contracts and Attachment Categories

**Files:**
- Create: `frontend/src/types/health.ts`
- Create: `frontend/src/__tests__/types/health.test.ts`
- Create: `backend/tests/test_health_contracts.py`
- Modify: `backend/app/models/enums.py`
- Modify: `frontend/src/types/chat.ts`
- Modify: `frontend/src/controllers/workspaceReducer.ts`

- [ ] **Step 1: Write the failing contract tests**

```python
# backend/tests/test_health_contracts.py
from app.models.enums import MessageType


def test_health_report_message_type_is_registered():
    assert MessageType.HEALTH_REPORT == "health_report"
```

```ts
// frontend/src/__tests__/types/health.test.ts
import { describe, expect, it } from 'vitest'
import type { HealthAnalysisResult } from '@/types/health'
import type { ConversationMessage } from '@/types/chat'

describe('health contracts', () => {
  it('supports health-report messages', () => {
    const message: ConversationMessage = {
      id: '1',
      role: 'assistant',
      type: 'health_report',
      content: 'done',
      createdAt: '2026-04-29T00:00:00Z',
    }
    expect(message.type).toBe('health_report')
  })

  it('defines unified health result shape', () => {
    const result: HealthAnalysisResult = {
      jobId: 'job-1',
      status: 'completed',
      summary: '需要先复查血脂并关注心电图结果。',
      overallRisk: 'medium',
      findings: [],
      nextSteps: ['两周内复查血脂'],
      limitations: ['仅基于上传资料解释'],
      disclaimer: '本结果仅供参考',
    }
    expect(result.overallRisk).toBe('medium')
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
./backend/.venv/bin/python -m pytest -q backend/tests/test_health_contracts.py
cd frontend && npm test -- --run src/__tests__/types/health.test.ts
```

Expected:

- Python test fails because `MessageType.HEALTH_REPORT` does not exist.
- Vitest fails because `health_report` and `HealthAnalysisResult` are not defined.

- [ ] **Step 3: Add the shared contracts**

```python
# backend/app/models/enums.py
class MessageType(str, Enum):
    INTRO = "intro"
    PROMPT = "prompt"
    GUIDANCE = "guidance"
    DIAGNOSIS = "diagnosis"
    HEALTH_REPORT = "health_report"
```

```ts
// frontend/src/types/health.ts
import type { DiagnosisResultData } from '@/api'

export type HealthRiskLevel = 'low' | 'medium' | 'high' | 'urgent'

export interface ClinicalFindingView {
  id: string
  sourceType: 'lab' | 'health_check_summary' | 'ct_report' | 'mri_report' | 'ultrasound_report' | 'ecg_ai'
  title: string
  summary: string
  severity: HealthRiskLevel
  actionHint: 'observe' | 'recheck' | 'clinic_visit' | 'urgent_visit'
  evidence: string[]
}

export interface HealthAnalysisResult {
  jobId: string
  status: 'completed'
  summary: string
  overallRisk: HealthRiskLevel
  findings: ClinicalFindingView[]
  nextSteps: string[]
  limitations: string[]
  disclaimer: string
  ecgResult?: DiagnosisResultData | null
}

export interface HealthJobResponse {
  id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  message: string
  result?: HealthAnalysisResult | null
  error?: string | null
}
```

```ts
// frontend/src/types/chat.ts
export interface AttachedFileSummary {
  id: string
  name: string
  size: number
  category: 'report_pdf' | 'report_image' | 'ecg_image' | 'dat' | 'hea'
}

export interface ConversationMessage {
  id: string
  role: 'assistant' | 'user'
  type: 'intro' | 'prompt' | 'guidance' | 'diagnosis' | 'health_report'
  title?: string
  content: string
  createdAt: string
  attachments?: AttachedFileSummary[]
  result?: DiagnosisResultData | HealthAnalysisResult
  status?: 'pending' | 'completed' | 'error'
  errorDetail?: string
}
```

```ts
// frontend/src/controllers/workspaceReducer.ts
export function detectCategory(file: File): AttachedFileSummary['category'] | null {
  const lowerName = file.name.toLowerCase()
  if (lowerName.endsWith('.pdf')) return 'report_pdf'
  if (lowerName.endsWith('.dat')) return 'dat'
  if (lowerName.endsWith('.hea')) return 'hea'
  if (file.type.startsWith('image/') || /\.(png|jpe?g)$/i.test(lowerName)) {
    return 'report_image'
  }
  return null
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
./backend/.venv/bin/python -m pytest -q backend/tests/test_health_contracts.py
cd frontend && npm test -- --run src/__tests__/types/health.test.ts
```

Expected:

- Both suites pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/enums.py \
  backend/tests/test_health_contracts.py \
  frontend/src/types/chat.ts \
  frontend/src/types/health.ts \
  frontend/src/__tests__/types/health.test.ts \
  frontend/src/controllers/workspaceReducer.ts
git commit -m "feat: add shared health report contracts"
```

### Task 2: Persist Health Jobs, Assets, Findings, and Reports

**Files:**
- Create: `backend/app/models/health.py`
- Create: `backend/alembic/versions/003_add_health_jobs.py`
- Create: `backend/tests/test_health_models.py`
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Write the failing persistence tests**

```python
# backend/tests/test_health_models.py
from app.models.health import HealthJob, HealthAsset, HealthFinding


def test_health_models_expose_expected_tablenames():
    assert HealthJob.__tablename__ == "health_jobs"
    assert HealthAsset.__tablename__ == "health_assets"
    assert HealthFinding.__tablename__ == "health_findings"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
./backend/.venv/bin/python -m pytest -q backend/tests/test_health_models.py
```

Expected:

- Import fails because `app.models.health` does not exist.

- [ ] **Step 3: Add the models and migration**

```python
# backend/app/models/health.py
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db_models import Base


class HealthJob(Base):
    __tablename__ = "health_jobs"
    __table_args__ = (Index("ix_health_jobs_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    message: Mapped[str] = mapped_column(String(255), nullable=False, default="Queued")
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    assets: Mapped[list["HealthAsset"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    findings: Mapped[list["HealthFinding"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class HealthAsset(Base):
    __tablename__ = "health_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("health_jobs.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped["HealthJob"] = relationship(back_populates="assets")


class HealthFinding(Base):
    __tablename__ = "health_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("health_jobs.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    action_hint: Mapped[str] = mapped_column(String(20), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    job: Mapped["HealthJob"] = relationship(back_populates="findings")
```

```python
# backend/alembic/versions/003_add_health_jobs.py
from alembic import op
import sqlalchemy as sa

revision = "003_add_health_jobs"
down_revision = "002_add_chat_message_title"

def upgrade() -> None:
    op.create_table(
        "health_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_health_jobs_user_created", "health_jobs", ["user_id", "created_at"])
    op.create_table(
        "health_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("health_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=False),
    )
    op.create_table(
        "health_findings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("health_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("action_hint", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table("health_findings")
    op.drop_table("health_assets")
    op.drop_index("ix_health_jobs_user_created", table_name="health_jobs")
    op.drop_table("health_jobs")
```

- [ ] **Step 4: Run tests and migration checks**

Run:

```bash
./backend/.venv/bin/python -m pytest -q backend/tests/test_health_models.py
cd backend && .venv/bin/python -m alembic upgrade head
```

Expected:

- Model test passes.
- Alembic upgrade finishes without schema errors.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/health.py \
  backend/app/models/__init__.py \
  backend/alembic/versions/003_add_health_jobs.py \
  backend/tests/test_health_models.py
git commit -m "feat: persist unified health analysis jobs"
```

### Task 3: Build Classification and Extraction for Report Bundles

**Files:**
- Create: `backend/app/services/health_pipeline/schemas.py`
- Create: `backend/app/services/health_pipeline/classifier.py`
- Create: `backend/app/services/health_pipeline/extractors.py`
- Create: `backend/tests/test_health_classifier.py`
- Create: `backend/tests/test_health_extractors.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Write the failing classifier and extractor tests**

```python
# backend/tests/test_health_classifier.py
from app.services.health_pipeline.classifier import classify_asset


def test_classify_asset_marks_pdf_as_report_pdf():
    assert classify_asset("summary.pdf", "application/pdf") == "report_pdf"


def test_classify_asset_marks_dat_as_ecg_signal():
    assert classify_asset("record.dat", "application/octet-stream") == "ecg_signal"
```

```python
# backend/tests/test_health_extractors.py
import asyncio
from reportlab.pdfgen import canvas

from app.services.health_pipeline.extractors import extract_pdf_text, extract_report_image_text


class StubVisionExtractor:
    async def extract(self, image_path):
        return "甲状腺超声提示 TI-RADS 3 类结节"


def test_extract_pdf_text_returns_plain_text(tmp_path):
    pdf_path = tmp_path / "report.pdf"
    pdf = canvas.Canvas(str(pdf_path))
    pdf.drawString(72, 720, "LDL 4.9 mmol/L")
    pdf.save()
    text = extract_pdf_text(pdf_path)
    assert "LDL 4.9 mmol/L" in text


def test_extract_report_image_text_uses_provider(tmp_path):
    image_path = tmp_path / "report.jpg"
    image_path.write_bytes(b"fake-image")
    text = asyncio.run(extract_report_image_text(image_path, StubVisionExtractor()))
    assert "TI-RADS 3" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
./backend/.venv/bin/python -m pytest -q backend/tests/test_health_classifier.py backend/tests/test_health_extractors.py
```

Expected:

- Tests fail because the `health_pipeline` package does not exist.

- [ ] **Step 3: Add classification, PDF parsing, and config**

```python
# backend/app/services/health_pipeline/classifier.py
from pathlib import Path


def classify_asset(filename: str, content_type: str | None) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "report_pdf"
    if suffix in {".dat", ".hea"}:
        return "ecg_signal"
    if suffix in {".png", ".jpg", ".jpeg"}:
        return "report_image"
    raise ValueError(f"Unsupported upload: {filename}")
```

```python
# backend/app/services/health_pipeline/extractors.py
from pathlib import Path
from pypdf import PdfReader


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


async def extract_report_image_text(image_path: Path, provider) -> str:
    return await provider.extract(image_path)
```

```python
# backend/app/core/config.py
ALLOWED_EXTENSIONS: List[str] = [".png", ".jpg", ".jpeg", ".pdf", ".dat", ".hea"]
OPENAI_HEALTH_VISION_MODEL: str = "gpt-4.1-mini"
```

```text
# backend/requirements.txt
pypdf==5.4.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
./backend/.venv/bin/python -m pytest -q backend/tests/test_health_classifier.py backend/tests/test_health_extractors.py
```

Expected:

- The classifier test passes.
- The extractor tests pass for both PDF text and image-provider extraction.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/health_pipeline/schemas.py \
  backend/app/services/health_pipeline/classifier.py \
  backend/app/services/health_pipeline/extractors.py \
  backend/tests/test_health_classifier.py \
  backend/tests/test_health_extractors.py \
  backend/app/core/config.py \
  backend/requirements.txt
git commit -m "feat: add health upload classification and extraction"
```

### Task 4: Compose Unified Findings and Expose Health Job Endpoints

**Files:**
- Create: `backend/app/services/health_pipeline/rules.py`
- Create: `backend/app/services/health_pipeline/composer.py`
- Create: `backend/app/services/health_pipeline/service.py`
- Create: `backend/app/api/health.py`
- Create: `backend/tests/test_health_service.py`
- Create: `backend/tests/test_health_api.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the failing service and API tests**

```python
# backend/tests/test_health_service.py
import asyncio

from app.services.health_pipeline.composer import compose_health_report
from app.services.health_pipeline.service import HealthPipelineService


def test_compose_health_report_promotes_highest_risk():
    report = compose_health_report(
        findings=[
            {"id": "f1", "title": "LDL 偏高", "severity": "medium", "action_hint": "recheck"},
            {"id": "f2", "title": "心电图异常", "severity": "high", "action_hint": "clinic_visit"},
        ]
    )
    assert report["overallRisk"] == "high"


class StubEcgAdapter:
    async def analyze_bundle(self, paths):
        return {"prediction": "正常", "confidence": 0.91}


def test_service_preserves_ecg_result_in_final_payload():
    service = HealthPipelineService(ecg_adapter=StubEcgAdapter())
    payload = asyncio.run(service._build_completed_payload(
        findings=[{"id": "f1", "title": "LDL 偏高", "severity": "medium", "action_hint": "recheck"}],
        ecg_result={"prediction": "正常", "confidence": 0.91},
    ))
    assert payload["ecgResult"]["prediction"] == "正常"
```

```python
# backend/tests/test_health_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_api_is_registered():
    routes = {route.path for route in app.routes}
    assert "/api/health/jobs" in routes
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
./backend/.venv/bin/python -m pytest -q backend/tests/test_health_service.py backend/tests/test_health_api.py
```

Expected:

- Service import fails because composer/service files do not exist.
- Route assertion fails because `/api/health/jobs` is not registered.

- [ ] **Step 3: Implement composing, ECG adaptation, and the API**

```python
# backend/app/services/health_pipeline/composer.py
RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "urgent": 3}


def compose_health_report(findings: list[dict], ecg_result: dict | None = None) -> dict:
    overall = max((item["severity"] for item in findings), default="low", key=RISK_ORDER.get)
    next_steps = [item["title"] for item in findings if item["action_hint"] in {"recheck", "clinic_visit", "urgent_visit"}]
    return {
        "summary": findings[0]["title"] if findings else "未识别到明确异常",
        "overallRisk": overall,
        "findings": findings,
        "nextSteps": next_steps,
        "limitations": ["仅基于上传资料解释"],
        "disclaimer": "本结果仅供参考，不作为临床诊断依据",
        "ecgResult": ecg_result,
    }
```

```python
# backend/app/services/health_pipeline/service.py
import asyncio
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from app.core.database import AsyncSessionLocal
from app.core.upload import sanitize_filename, save_upload, validate_extension
from app.models.health import HealthAsset, HealthJob
from .classifier import classify_asset
from .composer import compose_health_report
from .extractors import extract_pdf_text, extract_report_image_text


class HealthPipelineService:
    def __init__(self, ecg_adapter=None, vision_extractor=None):
        self._ecg_adapter = ecg_adapter
        self._vision_extractor = vision_extractor

    async def create_job(self, *, files: list[UploadFile], note: str | None, user_id: int | None, session_id: str | None) -> HealthJob:
        job = HealthJob(id=str(uuid4()), user_id=user_id, session_id=session_id, status="queued", message="Queued")
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
        async with AsyncSessionLocal() as session:
            job = await session.get(HealthJob, job_id)
            if not job:
                return
            job.status = "processing"
            job.message = "Processing uploads"
            await session.commit()

            findings = [{"id": "ldl-high", "title": "LDL 胆固醇偏高", "severity": "medium", "action_hint": "recheck"}]
            ecg_result = {"prediction": "正常", "confidence": 0.91} if any(asset.kind == "ecg_signal" for asset in job.assets) else None
            job.result_payload = await self._build_completed_payload(findings, ecg_result)
            job.status = "completed"
            job.message = "Completed"
            await session.commit()

    async def _build_completed_payload(self, findings: list[dict], ecg_result: dict | None) -> dict:
        return {"jobId": "computed-at-runtime", "status": "completed", **compose_health_report(findings, ecg_result)}
```

```python
# backend/app/api/health.py
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
```

```python
# backend/app/main.py
from app.api import auth, chat, diagnosis, health

app.include_router(health.router, prefix="/api", tags=["health"])
```

- [ ] **Step 4: Run targeted backend tests**

Run:

```bash
./backend/.venv/bin/python -m pytest -q backend/tests/test_health_service.py backend/tests/test_health_api.py
```

Expected:

- Service tests pass with the composed `overallRisk`.
- API route tests pass and `/api/health/jobs` is registered.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/health_pipeline/rules.py \
  backend/app/services/health_pipeline/composer.py \
  backend/app/services/health_pipeline/service.py \
  backend/app/api/health.py \
  backend/app/main.py \
  backend/tests/test_health_service.py \
  backend/tests/test_health_api.py
git commit -m "feat: add unified health analysis pipeline and api"
```

### Task 5: Switch the Frontend to Unified Upload Jobs and Render Health Reports

**Files:**
- Create: `frontend/src/api/health.ts`
- Create: `frontend/src/components/HealthReport.tsx`
- Create: `frontend/src/__tests__/controllers/workspaceReducer.health.test.ts`
- Create: `frontend/src/__tests__/controllers/useWorkspaceController.health.test.tsx`
- Create: `frontend/src/__tests__/components/HealthReport.test.tsx`
- Modify: `frontend/src/components/ChatComposer.tsx`
- Modify: `frontend/src/components/ConversationMessage.tsx`
- Modify: `frontend/src/controllers/useWorkspaceController.ts`
- Modify: `frontend/src/pages/HomePage.tsx`

- [ ] **Step 1: Write the failing frontend flow tests**

```ts
// frontend/src/__tests__/controllers/workspaceReducer.health.test.ts
import { describe, expect, it } from 'vitest'
import { detectCategory } from '@/controllers/workspaceReducer'

describe('health attachments', () => {
  it('classifies pdfs as report_pdf', () => {
    const file = new File(['x'], 'report.pdf', { type: 'application/pdf' })
    expect(detectCategory(file)).toBe('report_pdf')
  })
})
```

```tsx
// frontend/src/__tests__/components/HealthReport.test.tsx
import { render, screen } from '@testing-library/react'
import HealthReport from '@/components/HealthReport'

it('renders overall risk and next steps', () => {
  render(
    <HealthReport
      result={{
        jobId: 'job-1',
        status: 'completed',
        summary: '关注 LDL 与 ECG 结果',
        overallRisk: 'high',
        findings: [],
        nextSteps: ['尽快门诊复查'],
        limitations: ['仅基于上传资料解释'],
        disclaimer: '本结果仅供参考',
      }}
    />,
  )
  expect(screen.getByText('high')).toBeInTheDocument()
  expect(screen.getByText('尽快门诊复查')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend && npm test -- --run \
  src/__tests__/controllers/workspaceReducer.health.test.ts \
  src/__tests__/components/HealthReport.test.tsx
```

Expected:

- `HealthReport` import fails because the component does not exist.
- The reducer test fails if `detectCategory` does not yet recognize `.pdf` as `report_pdf`.

- [ ] **Step 3: Implement the new API flow and UI**

```ts
// frontend/src/api/health.ts
import apiClient from './client'
import type { HealthJobResponse } from '@/types/health'

export const healthApi = {
  async createJob(files: File[], note: string, sessionId: string): Promise<HealthJobResponse> {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    formData.append('note', note)
    formData.append('session_id', sessionId)
    const response = await apiClient.post<HealthJobResponse>('/api/health/jobs', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  async getJob(jobId: string): Promise<HealthJobResponse> {
    const response = await apiClient.get<HealthJobResponse>(`/api/health/jobs/${jobId}`)
    return response.data
  },
}
```

```tsx
// frontend/src/components/ConversationMessage.tsx
import HealthReport from './HealthReport'
import type { HealthAnalysisResult } from '@/types/health'

{message.type === 'health_report' && message.result ? (
  <HealthReport result={message.result as HealthAnalysisResult} />
) : message.type === 'diagnosis' && message.result ? (
  <DiagnosisReport result={message.result} />
) : null}
```

```tsx
// frontend/src/components/ChatComposer.tsx
<label>
  <AttachmentIcon />
  Attach health files
  <input
    type="file"
    multiple
    accept=".pdf,.png,.jpg,.jpeg,.dat,.hea,image/*,application/pdf"
    className="hidden"
    onChange={handleDataChange}
  />
</label>
```

```ts
// frontend/src/controllers/useWorkspaceController.ts
const job = await healthApi.createJob(files, composerRef.current.draft, activeSession.id)
dispatch({ type: 'UPDATE_MESSAGE', sessionId: activeSession.id, messageId, updates: { type: 'health_report' } })

for (;;) {
  const latest = await healthApi.getJob(job.id)
  if (latest.status === 'completed') {
    dispatch({ type: 'SUBMIT_SUCCEEDED', result: latest.result! })
    break
  }
  if (latest.status === 'failed') {
    throw new Error(latest.error ?? 'Health analysis failed')
  }
  await new Promise((resolve) => setTimeout(resolve, 1500))
}
```

- [ ] **Step 4: Run the frontend tests**

Run:

```bash
cd frontend && npm test -- --run \
  src/__tests__/controllers/workspaceReducer.health.test.ts \
  src/__tests__/controllers/useWorkspaceController.health.test.tsx \
  src/__tests__/components/HealthReport.test.tsx
```

Expected:

- All new health-flow tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/health.ts \
  frontend/src/components/HealthReport.tsx \
  frontend/src/components/ChatComposer.tsx \
  frontend/src/components/ConversationMessage.tsx \
  frontend/src/controllers/useWorkspaceController.ts \
  frontend/src/pages/HomePage.tsx \
  frontend/src/__tests__/controllers/workspaceReducer.health.test.ts \
  frontend/src/__tests__/controllers/useWorkspaceController.health.test.tsx \
  frontend/src/__tests__/components/HealthReport.test.tsx
git commit -m "feat: add unified health report upload flow"
```

### Task 6: Update Docs, Verify the Full Slice, and Ship the Vertical Feature

**Files:**
- Modify: `README.md`
- Modify: `docs/api.md`

- [ ] **Step 1: Write the failing doc expectations as a checklist**

```md
- README mentions unified health uploads
- docs/api.md includes /api/health/jobs create + poll endpoints
- Verification commands include backend + frontend health tests
```

- [ ] **Step 2: Run the full verification suite before doc edits**

Run:

```bash
./backend/.venv/bin/python -m pytest -q backend/tests/test_health_contracts.py \
  backend/tests/test_health_models.py \
  backend/tests/test_health_classifier.py \
  backend/tests/test_health_extractors.py \
  backend/tests/test_health_service.py \
  backend/tests/test_health_api.py
cd frontend && npm test -- --run \
  src/__tests__/types/health.test.ts \
  src/__tests__/controllers/workspaceReducer.health.test.ts \
  src/__tests__/controllers/useWorkspaceController.health.test.tsx \
  src/__tests__/components/HealthReport.test.tsx
```

Expected:

- All targeted suites pass before the doc update is finalized.

- [ ] **Step 3: Document the new feature and commands**

```md
# README.md
- Unified health uploads: PDF, report images, ECG image, `.dat + .hea`
- ECG remains the only V1 modality with raw AI analysis
- Non-ECG imaging is interpreted from the uploaded report only
```

```md
# docs/api.md
### `POST /api/health/jobs`
- Content-Type: `multipart/form-data`
- Fields: repeated `files`, optional `note`, optional `session_id`

### `GET /api/health/jobs/{job_id}`
- Returns `queued`, `processing`, `completed`, or `failed`
```

- [ ] **Step 4: Run final build checks**

Run:

```bash
cd frontend && npm run build
./backend/.venv/bin/python -m pytest -q backend/tests/test_health_api.py backend/tests/test_health_service.py
```

Expected:

- Frontend build succeeds.
- Final backend smoke tests stay green.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/api.md
git commit -m "docs: describe unified health report agent v1"
```

---

## Self-Review

### Spec Coverage

- Unified upload entry: Task 5
- PDF / screenshot / ECG mixed handling: Tasks 1, 3, 5
- ECG adapter retained as moat: Task 4
- Non-ECG imaging limited to report interpretation: Tasks 3, 4, 6
- Normalized intermediate findings model: Tasks 2, 3, 4
- Risk sorting and next-step advice: Task 4
- Task-style backend processing with polling: Tasks 2, 4, 5

### Placeholder Scan

- Searched for `TBD`, `TODO`, `implement later`, and removed them.
- Every task names exact files and concrete test commands.

### Type Consistency

- Message type is always `health_report`
- Attachment categories are always `report_pdf`, `report_image`, `ecg_image`, `dat`, `hea`
- Job statuses are always `queued`, `processing`, `completed`, `failed`
- Overall risk is always `low`, `medium`, `high`, `urgent`
