# ECG Diagnosis Suite - Backend

FastAPI backend for ECG diagnosis system.

## Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

After starting the server, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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
