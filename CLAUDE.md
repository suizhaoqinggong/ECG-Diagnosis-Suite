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

Backend formatting: `black app/ && isort app/`
Backend type check: `mypy app/`

### Docker Compose

```bash
docker compose up --build   # backend(:8000), frontend(:80), MySQL(:3306)
```

## Architecture

### Backend (`backend/`)

- **Entry**: `app/main.py` — FastAPI app with lifespan handler, CORS, mounts routers under `/api`
- **Config**: `app/core/config.py` — Pydantic `BaseSettings`, loads from `backend/.env`. Key settings: `DATABASE_URL`, `MODEL_CHECKPOINT_PATH`, `DEVICE`, upload/report dirs
- **API routers**:
  - `app/api/diagnosis.py` — `POST /api/diagnose` (image), `POST /api/diagnose-dat` (dat+hea pair), `GET /api/history`. Uses `SYMPTOM_DATABASE` dict for severity/ICD code lookup and saves records via SQLAlchemy
  - `app/api/conduction_disorder.py` — `POST /api/detect/conduction-disorder` with lazy singleton detector
- **Services**:
  - `app/services/diagnosis_report_service.py` — generates enhanced reports (template-based or LLM-enhanced)
  - `app/services/ecg_dat_loader.py` — loads `.dat`/`.hea` files via `wfdb`, resamples to target shape
- **ML models** (`backend/ml/`):
  - `cardioformer_service.py` — singleton service wrapping CardioFormer; `predict_from_image()` converts image→signal then runs model, `predict_from_signal()` runs directly
  - `cardioformer_model.py` — CardioFormer architecture
  - `resnet1d_model.py` — ResNet1D baseline for conduction disorder detection
  - `conduction_disorder_detector.py` — specialized detector using `ECGImageToSignal` adapter
  - `ecg_image_converter.py` — `ECGImageToSignal` converts ECG printout images to 12-lead 1D signals
- **DB models**: `app/models/db_models.py` — SQLAlchemy ORM `DiagnosisRecord`, persisted via async sessions
- **Database**: `app/core/database.py` — async engine, defaults to SQLite, configurable to MySQL via `DATABASE_URL`

### Frontend (`frontend/`)

- **Entry**: `src/main.tsx` → `src/App.tsx` → `src/pages/HomePage.tsx`
- **State management**: `src/controllers/useWorkspaceController.ts` — a single `useReducer` hook managing all workspace state (sessions, composer, submission, UI). State shape: `WorkspaceState` with `persisted`, `composer`, `submission`, `ui` slices
- **Persistence**: sessions auto-saved to `localStorage` key `ecg-persisted` when `persistenceEnabled` is true
- **API layer**: `src/api/client.ts` (axios instance with 120s timeout) + `src/api/index.ts` (`diagnosisApi` with progress callbacks and abort support)
- **Types**: `src/types/chat.ts` — `ChatSession`, `ConversationMessage`, `AttachedFileSummary`
- **Path alias**: `@/` maps to `src/` (configured in `vite.config.ts`, `vitest.config.ts`, and `tsconfig.json`)
- **Testing**: Vitest with jsdom, `@testing-library/react`, setup file at `src/__tests__/setup.ts`

### Request Flow (Diagnosis)

1. User attaches file(s) in `ChatComposer`, optionally adds clinical note, submits
2. `useWorkspaceController.submit()` validates file combination, appends user + pending messages to active session
3. Calls `diagnosisApi.diagnoseImage()` or `diagnosisApi.diagnoseDatPair()` with upload progress and abort signal
4. Frontend proxy (`vite.config.ts`) forwards `/api` to `localhost:8000`
5. Backend saves upload, loads image/signal, runs CardioFormer inference
6. Response includes prediction, confidence, severity, ICD code, recommendations, and enhanced report
7. Frontend updates pending message with result, persists session to localStorage

## Key Conventions

- **API prefix**: all backend endpoints mounted under `/api` in `main.py`. Frontend uses relative `/api/...` paths, relying on Vite proxy (dev) or Nginx proxy (Docker)
- **File-system data**: uploads stored under `backend/data/uploads`, reports under `backend/data/reports` — multiple modules reference these via `settings.resolve_backend_path()`
- **Model checkpoints**: searched in order — `backend/models/checkpoints/best.ckpt`, then `backend/models/weights/`, then `models/` at project root. Override via `MODEL_CHECKPOINT_PATH` env var
- **ML tensor shape**: models expect `[batch, 12, 1000]` (12-lead, 1000 samples)
- **Diagnosis categories**: PTB-XL superclasses — 正常, 心肌梗死, ST-T改变, 传导障碍, 心室肥大 (defined in `SYMPTOM_DATABASE`)
- **Medical disclaimer**: must appear in API responses and UI when touching diagnosis features
- **File attachment rules**: single ECG image OR matched `.dat + `.hea` pair (same basename); no mixing
