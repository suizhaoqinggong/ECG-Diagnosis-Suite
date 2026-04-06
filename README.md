# ECG Diagnosis Suite

ECG Diagnosis Suite is a FastAPI + React project for ECG image and signal classification. The current repository is an engineering-focused MVP: the end-to-end diagnosis flow is wired up, local MySQL support is configured, and Docker Compose now uses MySQL as the database service.

## Current Status

- Frontend upload flow is available for ECG images and `.dat + .hea` pairs.
- Backend diagnosis APIs, history persistence, and model loading are implemented.
- Local development now uses `uv` for the Python environment and MySQL for persistence.
- Docker Compose has been switched from PostgreSQL to MySQL.
- PDF export code exists in the backend, but the frontend export action is still not connected.

## Main Features

- ECG image upload: `.png`, `.jpg`, `.jpeg`
- ECG signal upload: `.dat` + `.hea`
- AI diagnosis with CardioFormer-based service
- Conduction disorder detection endpoint
- Diagnosis history persistence
- Local MySQL and Docker MySQL support

## Tech Stack

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Axios

### Backend

- FastAPI
- SQLAlchemy
- MySQL / SQLite / PostgreSQL-compatible configuration
- PyTorch
- OpenCV

### Environment

- `uv` for Python environment management
- Homebrew MySQL for local development
- Docker Compose for containerized deployment

## Repository Layout

```text
ECG-Diagnosis-Suite/
├── backend/                 # FastAPI backend
│   ├── app/                 # API, config, DB models, services
│   ├── ml/                  # ECG model and preprocessing code
│   ├── .env.example         # Backend environment template
│   └── requirements.txt     # Python dependencies
├── frontend/                # React frontend
├── models/                  # Model checkpoints and weight placeholders
├── docs/                    # Development and deployment notes
├── scripts/                 # Utility scripts
├── docker-compose.yml       # Container orchestration
└── start.sh                 # Local backend bootstrap helper
```

## Local Development

### Requirements

- macOS / Linux
- Node.js 18+
- `uv`
- MySQL 8+ or Homebrew MySQL

### 1. Backend Setup with `uv`

```bash
cd backend
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r requirements.txt
```

The repo now expects a backend virtual environment at `backend/.venv`.

### 2. Configure Backend Environment

Create or edit `backend/.env`:

```env
DATABASE_URL=mysql+asyncmy://ecg:ecg123456@127.0.0.1:3306/ecg_db
```

The repository already includes an example at [backend/.env.example](/Users/azure/ECG-Diagnosis-Suite/backend/.env.example).

### 3. Start Local MySQL

If you use Homebrew MySQL:

```bash
brew services start mysql
mysql -u root
```

Recommended local database and user:

```sql
CREATE DATABASE IF NOT EXISTS ecg_db CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'ecg'@'localhost' IDENTIFIED BY 'ecg123456';
GRANT ALL PRIVILEGES ON ecg_db.* TO 'ecg'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Start Backend

From the project root:

```bash
./start.sh
```

Or manually:

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default address:

- `http://localhost:5173`

Backend default address:

- `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

## Docker Compose

The compose stack now uses MySQL instead of PostgreSQL.

```bash
docker compose up --build
```

Services:

- `backend`: FastAPI service on port `8000`
- `frontend`: static frontend on port `80`
- `db`: MySQL 8.4 on port `3306`
- `redis`: Redis 7 on port `6379`

## Production Deployment

The repository now includes a production stack for direct server deployment:

```bash
cp .env.production.example .env.production
bash scripts/deploy-production.sh
```

Production compose file:

- [docker-compose.prod.yml](/Users/azure/ECG-Diagnosis-Suite/docker-compose.prod.yml)

Production deployment guide:

- [docs/production-deployment.md](/Users/azure/ECG-Diagnosis-Suite/docs/production-deployment.md)

Container database credentials in [docker-compose.yml](/Users/azure/ECG-Diagnosis-Suite/docker-compose.yml):

- database: `ecg_db`
- user: `ecg`
- password: `ecg123456`
- root password: `root123456`

## Model Checkpoints

The backend searches CardioFormer checkpoints in this order:

- `backend/models/checkpoints/best.ckpt`
- `backend/models/weights/best.ckpt`
- `models/checkpoints/best.ckpt`
- `models/weights/best.ckpt`

You can also override this with:

```env
MODEL_CHECKPOINT_PATH=/absolute/path/to/best.ckpt
```

## API Surface

Primary endpoints:

- `POST /api/diagnose`
- `POST /api/diagnose-dat`
- `GET /api/chat/sessions`
- `POST /api/chat/sessions`
- `POST /api/detect/conduction-disorder`
- `GET /health`
- `GET /docs`

For request/response details, see [docs/api.md](/Users/azure/ECG-Diagnosis-Suite/docs/api.md).

## Notes and Limitations

- This project is for research and engineering use, not clinical diagnosis.
- Conversation history is managed through `/api/chat/*`; the legacy `/api/history` path has been removed from the backend.
- The frontend PDF export button is still not wired to a backend endpoint.
- Automated verification lives in `tests/`, `backend/tests/`, and `frontend/src/__tests__/`.

## License

MIT
