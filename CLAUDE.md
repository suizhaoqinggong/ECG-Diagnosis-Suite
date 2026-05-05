# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ECG Diagnosis Suite — a FastAPI + React app for ECG image and signal classification. Users upload ECG images (PNG/JPG) or matched `.dat + .hea` signal pairs, the backend runs inference via CardioFormer, and results are displayed in a document-like conversation UI. Bilingual (Chinese-first, English support).

## Build & Run Commands

### Backend (Python)

```bash
cd backend
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Or from project root: `./start.sh`

Database migrations (required for production, optional for dev):
```bash
cd backend
.venv/bin/alembic upgrade head            # apply all migrations
.venv/bin/alembic revision --autogenerate -m "description"   # create new migration
```

In development, if no `alembic_version` table exists, the app auto-creates tables via `Base.metadata.create_all`. In production, the app refuses to start without migrations applied.

### Frontend (Node.js)

```bash
cd frontend
npm install
npm run dev          # Vite dev server on :5173, proxies /api to :8000
npm run build        # tsc + vite build
npm run lint         # eslint
npm run test         # vitest (jsdom, globals: true)
npm run test:coverage
```

Single frontend test: `npx vitest run path/to/test.tsx`
Single backend test: `pytest tests/test_api.py::test_health_check`
All tests: `pytest tests/ backend/tests/`

Backend formatting: `black app/ && isort app/`
Backend type check: `mypy app/`

### Docker Compose

```bash
docker compose up --build   # backend(:8000), frontend(:80), MySQL(:3306)
```

## Architecture

### Backend (`backend/`)

- **Entry**: `app/main.py` — FastAPI app with lifespan handler. On startup: ensures runtime dirs, loads model service (production), initializes DB. On shutdown: disposes DB engine.
- **Config**: `app/core/config.py` — Pydantic `BaseSettings`, loads from `backend/.env` then `backend/.env.local` (override). Key settings: `DATABASE_URL`, `SECRET_KEY`, `DEVICE`, `MODEL_CHECKPOINT_PATH`, `ENVIRONMENT`, `RATE_LIMIT_BACKEND`. Includes `resolve_backend_path()` and `resolve_project_path()` helpers, and auto-discovers model checkpoints from multiple candidate paths.
- **Database**: `app/core/database.py` — async SQLAlchemy engine + session factory (`AsyncSessionLocal`). `init_db()` auto-creates tables in dev; in production, requires Alembic migrations. Maintains a global `database_status` singleton for health checks.
- **Security**: `app/core/security.py` — JWT access tokens (HS256, 15min) + refresh tokens (scrypt-hashed, 7 days). `get_password_hash()` uses scrypt.
- **Auth dependencies**: `app/core/auth_dependencies.py` — `get_current_user()` (required, raises 401) and `get_optional_user()` (returns None for anonymous). Both use `HTTPBearer` with `auto_error=False`.
- **Rate limiting**: `app/core/rate_limit.py` — sliding-window limiter, memory-backed in dev/test, database-backed in production (via `rate_limit_counter` table). Per-action limit presets: login (5/5min), register (3/hr), chat writes (30/min), etc.

#### API Routers

- `app/api/diagnosis.py` — `POST /api/diagnose` (image), `POST /api/diagnose-dat` (dat+hea pair). Delegates to `DiagnosisService` which orchestrates upload → signal conversion → model inference → quality gating → report generation → optional DB persistence (for authenticated users).
- `app/api/auth.py` — JWT auth: register, login, refresh (cookie-based), logout, me, change-password, delete-account. Login returns access token in body + refresh token as httpOnly cookie.
- `app/api/chat.py` — CRUD for chat sessions and messages: list/create/rename/delete sessions, fetch messages with cursor-based pagination.
- `app/api/health.py` — Health pipeline: `POST /api/health/jobs` (create job, returns immediately) + `GET /api/health/jobs/{job_id}` (poll for results). Routes uploads through classification, extraction, and report composition.

#### Services

- `app/services/diagnosis_service.py` — orchestrates the full ECG diagnosis pipeline with dependency injection for testability. Produces `DiagnosisResponse` (prediction, confidence, severity, ICD, recommendations, multi-label findings, quality warning).
- `app/services/diagnosis_report_service.py` — generates structured reports (template or LLM-enhanced) with severity/ICD/recommendations.
- `app/services/ecg_dat_loader.py` — loads `.dat`/`.hea` via `wfdb`, resamples to target shape `[12, 1000]`.
- `app/services/health_pipeline/` — unified health analysis: `service.py` (orchestration), `classifier.py` (routes uploads by type), `extractors.py` (per-modality data extraction), `composer.py` (builds unified report), `schemas.py` (data models), `rules.py` (severity/action classification).

#### ORM Models (SQLAlchemy, `backend/app/models/`)

- `db_models.py` — declarative `Base`
- `user.py` — `User` (email, hashed_password, is_active, created_at)
- `refresh_token.py` — `RefreshToken` (scrypt-hashed token, expiry, FK→user)
- `chat.py` — `ChatSession` (FK→user) and `ChatMessage` (FK→session, role/type/status enums, JSON attachments/results)
- `health.py` — `HealthJob` (status, result_payload, FK→user/session), `HealthAsset`, `HealthFinding`
- `rate_limit.py` — `RateLimitCounter` (window key + timestamp for DB-backed rate limiting)
- `enums.py` — `MessageRole`, `MessageType`, `MessageStatus`

#### ML Models (`backend/ml/`)

- `cardioformer_service.py` — singleton service; `predict_from_image()` converts image→signal then infers, `predict_from_signal()` infers directly. Checks for checkpoint; falls back to random initialization with a warning.
- `cardioformer_model.py` — CardioFormer architecture
- `ecg_image_converter.py` — `ECGImageToSignal` 6-stage pipeline: grid suppression, centroid extraction, normalization, layout detection, skew correction, QC warnings
- `conduction_disorder_detector.py` — specialized detector using `ECGImageToSignal` + `ResNet1DBaseline`
- `resnet1d_model.py` — ResNet1D baseline
- `image_validator.py`, `image_decoder.py`, `signal_quality.py` — preprocessing/quality utilities
- `pipeline_types.py` — shared type definitions for ML pipeline

#### Alembic (`backend/alembic/`)

Three migration versions:
- `001_initial_schema.py` — users, refresh_tokens, chat_sessions, chat_messages, diagnosis_records, rate_limit_counters
- `002_add_chat_message_title.py`
- `003_add_health_jobs.py` — health_jobs, health_assets, health_findings

### Frontend (`frontend/`)

- **Entry**: `src/main.tsx` → `src/App.tsx` → `src/pages/HomePage.tsx`
- **State management**: `src/controllers/useWorkspaceController.ts` — single `useReducer` hook over `WorkspaceState` with slices: `persisted` (sessions, activeSessionId, persistenceEnabled), `composer` (draft, attachments, pairStatus, validation), `submission` (phase, progress, error, canRetry), `ui` (dragging, sidebar, renaming, printable). Actions are dispatched by `workspaceReducer.ts`.
- **Controller split**: `workspaceReducer.ts` holds pure reducer logic + exported helpers (`detectCategory`, `validateAttachments`, `createEmptySession`, etc.). `useWorkspaceController.ts` holds side-effectful submit/retry/hydrate logic and wires API calls.
- **Persistence**: sessions auto-saved to `localStorage` key `ecg-persisted` via `StorageManager` (`src/utils/storage.ts`). Versioned at `STORAGE_VERSION` for schema migration.
- **Auth**: `src/auth/AuthProvider.tsx` — React context wrapping auth state. `src/auth/store.ts` — state shape. `src/auth/api.ts` — axios calls for register/login/refresh/logout. `UserMenu.tsx` / `AuthModal.tsx` — UI components. Refresh token is httpOnly cookie; frontend calls `/api/auth/me` on mount to check session.
- **API layer**: `src/api/client.ts` (axios instance, 120s timeout, interceptor for 401→refresh retry) + `src/api/index.ts` (diagnosisApi with progress callbacks and abort), `src/api/chat.ts` (session CRUD), `src/api/health.ts` (job create + poll).
- **Types**: `src/types/chat.ts` (`ChatSession`, `ConversationMessage`, `AttachedFileSummary`), `src/types/health.ts` (`HealthAnalysisResult`, `ClinicalFindingView`, `HealthRiskLevel`)
- **Path alias**: `@/` → `src/` (configured in vite, vitest, and tsconfig)
- **Testing**: Vitest with jsdom, `@testing-library/react`, setup at `src/__tests__/setup.ts`

### Request Flow (Diagnosis)

1. User attaches file(s) in `ChatComposer`, optionally adds clinical note, submits
2. `useWorkspaceController.submit()` validates file combination, appends user + pending messages
3. Calls `diagnosisApi.diagnoseImage()` or `diagnosisApi.diagnoseDatPair()` with upload progress + abort
4. Vite proxy forwards `/api` to `localhost:8000`
5. `DiagnosisService` saves upload, decodes image, converts to signal, runs CardioFormer, applies quality gating, generates report
6. For authenticated users, persists a `ChatMessage` with the result to the database
7. Frontend updates pending message with result, persists session to localStorage

### Request Flow (Health Pipeline)

1. Frontend calls `POST /api/health/jobs` with files + optional note/session_id — returns job ID immediately
2. Frontend polls `GET /api/health/jobs/{job_id}` until status is `completed` or `failed`
3. Backend `HealthPipelineService` classifies uploads, extracts data per modality (ECG→AI inference, reports→extraction), composes unified report with findings array + risk level + next steps
4. Results persisted as `HealthJob` + `HealthFinding` rows, returned as `HealthAnalysisResult` to frontend

### Test Structure

Three test directories:
- `tests/` — cross-cutting regression + security tests (auth API, chat API, diagnosis API, upload security, error leak hardening, rate limiting, production runtime)
- `backend/tests/` — backend unit + integration tests (health pipeline tests ×6, image processing, signal quality, ECG converter, rate limiting, diagnosis service)
- `frontend/src/__tests__/` — frontend unit tests (components, controllers, types, API client, utils)

Run all: `pytest tests/ backend/tests/`
Run backend only: `pytest backend/tests/`
Run cross-cutting: `pytest tests/`

## Key Conventions

- **API prefix**: all backend endpoints mounted under `/api` in `main.py`. Frontend uses relative `/api/...` paths, relying on Vite proxy (dev) or Nginx proxy (Docker).
- **File-system data**: uploads under `data/uploads/`, reports under `data/reports/` (both relative to project root). Use `settings.upload_dir_path` / `settings.report_output_dir_path` rather than hardcoding paths.
- **Model checkpoints**: searched in order via `settings.get_model_checkpoint_path()`. Override with `MODEL_CHECKPOINT_PATH` env var.
- **ML tensor shape**: models expect `[batch, 12, 1000]` (12-lead, 1000 samples).
- **Diagnosis categories**: PTB-XL superclasses — 正常, 心肌梗死, ST-T改变, 传导障碍, 心室肥大
- **Medical disclaimer**: must appear in API responses and UI when touching diagnosis features.
- **File attachment rules**: single ECG image OR matched `.dat + `.hea` pair (same basename); health pipeline additionally accepts PDFs and report images.
- **Auth pattern**: diagnosis/health endpoints use `get_optional_user` (anonymous OK, auth optionally links to user). Chat endpoints require `get_current_user`. Refresh token is httpOnly cookie; access token is short-lived (15min) with refresh endpoint.
- **Environment**: `ENVIRONMENT=development` (default) vs `production`. Production requires: non-default `SECRET_KEY`, Alembic migrations applied, model checkpoint loaded at startup, `DEBUG=False`.
- **Database URL**: defaults to SQLite (`sqlite+aiosqlite:///./ecg_db.sqlite`). For MySQL: `mysql+asyncmy://ecg:ecg123456@127.0.0.1:3306/ecg_db`.
