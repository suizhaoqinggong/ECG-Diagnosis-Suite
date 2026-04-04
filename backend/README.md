# ECG Diagnosis Suite - Backend

FastAPI backend for ECG diagnosis system.

## Development

```bash
# Create virtual environment
uv venv .venv --python 3.11

# Install dependencies
uv pip install --python .venv/bin/python -r requirements.txt

# Run development server
.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run backend tests
pytest -q tests
```

If `backend/.env` is not configured, the app falls back to local SQLite.
For MySQL, copy `backend/.env.example` and set `DATABASE_URL`.

## API Documentation

After starting the server, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Manual Checks

Legacy ad hoc model/debug scripts were moved to
`scripts/manual_checks/` so they do not break automated pytest runs.

## Project Structure

```
backend/
├── app/
│   ├── api/          # API routes
│   ├── core/         # Configuration
│   ├── models/       # Database models
│   ├── services/     # Business logic
│   └── main.py       # Application entry
├── ml/               # ML models
├── utils/            # Utility functions
└── requirements.txt
```
