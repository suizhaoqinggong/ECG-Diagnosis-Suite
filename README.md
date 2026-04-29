# ECG Diagnosis Suite

AI-powered ECG diagnosis system with a FastAPI backend and React frontend. Users upload ECG images (PNG/JPG) or matched `.dat + .hea` signal pairs, the backend runs inference via a CardioFormer deep learning model, and results are displayed in a document-like conversation interface. Bilingual (Chinese-first, English support).

## Features

- **Unified health uploads**: report PDFs (`.pdf`), report images (`.png`, `.jpg`, `.jpeg`), ECG images, and matched `.dat` + `.hea` signal pairs
- **ECG image upload**: `.png`, `.jpg`, `.jpeg`
- **ECG signal upload**: matched `.dat` + `.hea` pairs (PTB-XL / WFDB format)
- **AI diagnosis**: CardioFormer-based classification across 5 diagnostic categories
- **Health pipeline**: unified job-based analysis (create + poll) that routes uploads through classification, extraction, and report composition. ECG is the only V1 modality with raw AI analysis; non-ECG imaging is interpreted from the uploaded report only.
- **Conduction disorder detection**: specialized endpoint with ResNet1D baseline
- **Conversation UI**: document-like session management with chat history persisted to database
- **Enhanced reports**: diagnosis-specific structured reports with severity, ICD codes, and recommendations
- **User authentication**: JWT-based registration, login, logout, password change, and account deletion
- **Security**: CORS enforcement, security headers (HSTS, X-Frame-Options, nosniff), rate limiting, error detail sanitization
- **PDF export**: report generator available in backend (frontend button pending wiring)
- **ECG preprocessing pipeline**: 6-stage image-to-signal conversion (grid suppression, centroid extraction, normalization, layout detection, skew correction, QC warnings)

## Tech Stack

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Axios
- Vitest + Testing Library

### Backend

- FastAPI
- SQLAlchemy (async) + Alembic migrations
- MySQL (production) / SQLite (local development)
- PyTorch + OpenCV
- WFDB (ECG signal I/O)
- Pytest

### Infrastructure

- Docker Compose (dev with MySQL, prod with nginx reverse proxy + optional TLS)
- JWT authentication (python-jose + bcrypt)

## Repository Layout

```text
ECG-Diagnosis-Suite/
├── backend/
│   ├── app/                 # API routes, config, DB models, services
│   ├── ml/                  # CardioFormer model, ECG preprocessing, detectors
│   ├── tests/               # Backend unit + integration tests
│   ├── alembic/             # Database migrations
│   ├── Dockerfile
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # UI components
│   │   ├── auth/            # Auth UI + state management
│   │   ├── controllers/     # Workspace reducer + controller hooks
│   │   ├── api/             # Backend API client layer
│   │   ├── pages/           # Page components
│   │   └── __tests__/       # Frontend tests
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── tests/                   # Cross-cutting regression + security tests
├── models/                  # Model checkpoints (best.ckpt)
├── docs/                    # API reference, architecture, deployment guides
├── data/                    # Uploads, reports, datasets
├── deploy/                  # Nginx templates and TLS certs
├── scripts/                 # Deployment and quick-start scripts
├── docker-compose.yml              # Development stack
├── docker-compose.prod.yml         # Production stack
├── docker-compose.prod.tls.yml     # TLS overlay
├── .env.production.example
├── start.sh
├── stop.sh
└── deploy.sh
```

## Local Development

### Requirements

- macOS / Linux
- Node.js 18+
- `uv`
- MySQL 8+ (or SQLite for quick start — set `DATABASE_URL=sqlite+aiosqlite:///./ecg_db.sqlite`)

### 1. Backend Setup

```bash
cd backend
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r requirements.txt
```

### 2. Configure Environment

Copy `backend/.env.example` to `backend/.env` and adjust as needed:

```env
DATABASE_URL=mysql+asyncmy://ecg:ecg123456@127.0.0.1:3306/ecg_db
```

For local SQLite (no MySQL install needed):

```env
DATABASE_URL=sqlite+aiosqlite:///./ecg_db.sqlite
```

### 3. Start MySQL (if using MySQL)

```bash
brew services start mysql
mysql -u root -e "
  CREATE DATABASE IF NOT EXISTS ecg_db CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
  CREATE USER IF NOT EXISTS 'ecg'@'localhost' IDENTIFIED BY 'ecg123456';
  GRANT ALL PRIVILEGES ON ecg_db.* TO 'ecg'@'localhost';
  FLUSH PRIVILEGES;
"
```

### 4. Start Backend

```bash
./start.sh
# OR manually:
cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

- Frontend: `http://localhost:5173`
- Backend: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

## Docker Compose

```bash
docker compose up --build
```

Services:

| Service | Port |
|---|---|
| backend (FastAPI) | 8000 |
| frontend (nginx) | 80 |
| db (MySQL 8.4) | 3306 |

Default credentials: database `ecg_db`, user `ecg`, password `ecg123456`.

## Production Deployment

```bash
cp .env.production.example .env.production
bash deploy.sh
```

The production stack adds an nginx reverse proxy and health checks. Optional TLS termination is available via `docker-compose.prod.tls.yml`. See [docs/production-deployment.md](docs/production-deployment.md) for details.

## Model Checkpoints

The backend searches for `best.ckpt` in this order:

1. `backend/models/checkpoints/best.ckpt`
2. `backend/models/weights/best.ckpt`
3. `models/checkpoints/best.ckpt`
4. `models/weights/best.ckpt`

Override with `MODEL_CHECKPOINT_PATH=/path/to/best.ckpt` in `backend/.env`.

Production startup requires a valid checkpoint — the backend exits on boot if none is found.

## API Surface

### Auth

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, returns JWT tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Logout, revoke refresh token |
| GET | `/api/auth/me` | Get current user profile |
| POST | `/api/auth/change-password` | Change password |
| POST | `/api/auth/delete-account` | Delete account (requires password confirmation) |

### Chat Sessions

| Method | Path | Description |
|---|---|---|
| GET | `/api/chat/sessions` | List user sessions |
| POST | `/api/chat/sessions` | Create session |
| GET | `/api/chat/sessions/{id}` | Get session detail |
| PATCH | `/api/chat/sessions/{id}` | Rename session |
| DELETE | `/api/chat/sessions/{id}` | Delete session |
| DELETE | `/api/chat/sessions` | Clear all sessions |
| GET | `/api/chat/sessions/{id}/messages` | Get session messages |

### Diagnosis

| Method | Path | Description |
|---|---|---|
| POST | `/api/diagnose` | Upload ECG image for diagnosis |
| POST | `/api/diagnose-dat` | Upload `.dat + .hea` pair for diagnosis |
| POST | `/api/detect/conduction-disorder` | Conduction disorder detection |

### Health Pipeline

| Method | Path | Description |
|---|---|---|
| POST | `/api/health/jobs` | Create a health analysis job (PDF, image, or signal uploads) |
| GET | `/api/health/jobs/{job_id}` | Poll job status and retrieve unified report result |

### System

| Method | Path | Description |
|---|---|---|
| GET | `/` | API info |
| GET | `/health` | Health check with database status |
| GET | `/docs` | Swagger UI |

For detailed request/response schemas, see [docs/api.md](docs/api.md) or the live Swagger UI.

## Notes and Limitations

- This project is for research and engineering demonstration, not clinical diagnosis.
- The PDF export service exists in the backend but the frontend download button is not yet wired.
- The legacy `/api/history` endpoint has been removed; session history is managed through `/api/chat/*`.
- The health pipeline currently uses stub extraction for report images; production deployments should configure an OpenAI-compatible vision provider via `OPENAI_HEALTH_VISION_MODEL`.
- Diagnosis endpoints support anonymous access; attaching a Bearer token writes results to the authenticated user's history.
- Automated tests live in `tests/`, `backend/tests/`, and `frontend/src/__tests__/`.
- Health-specific backend tests: `backend/tests/test_health_*.py` (6 files).
- Frontend health tests: `frontend/src/__tests__/types/health.test.ts` (+ additional tests pending Task 5).

## License

MIT
