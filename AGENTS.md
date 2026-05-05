# Repository Guidelines

## Project Structure & Module Organization
`backend/app/` holds the FastAPI app: routes in `api/`, settings in `core/`, ORM models in `models/`, and business logic in `services/`. ECG preprocessing and inference live in `backend/ml/`; migrations live in `backend/alembic/versions/`; backend tests live in `backend/tests/`. `frontend/src/` contains the React app, organized into `components/`, `pages/`, `auth/`, `api/`, `controllers/`, `types/`, `utils/`, and `__tests__/`. Checks live in `tests/`. Treat `data/`, `backend/data/uploads/`, `backend/data/reports/`, and `models/` as runtime assets unless updating fixtures.

## Build, Test, and Development Commands
- `cd backend && uv venv .venv --python 3.11 && uv pip install --python .venv/bin/python -r requirements.txt`: create the backend environment.
- `./start.sh`: start the backend from the repo root.
- `cd backend && .venv/bin/python -m alembic upgrade head`: apply schema migrations.
- `cd frontend && npm install && npm run dev`: start the frontend on `:5173`.
- `cd frontend && npm run build`: type-check and build production assets.
- `cd frontend && npm run lint`: run ESLint.
- `./backend/.venv/bin/python -m pytest -q tests backend/tests`: run Pytest.
- `cd frontend && npm test -- --run` or `npm run test:coverage`: run Vitest once, with optional coverage output.
- `docker compose up --build`: boot frontend, backend, and MySQL together.

## Coding Style & Naming Conventions
Use 4-space indentation in Python and format backend changes with `black app/ && isort app/`. Follow the existing 2-space indentation style in TypeScript/TSX. Use `PascalCase` for React components, `useCamelCase` for hooks, `snake_case.py` for Python modules, and `test_*.py` or `*.test.ts(x)` for tests. Keep endpoints under `/api` and preserve Chinese-first medical copy in diagnosis flows.

## Testing Guidelines
Backend tests use Pytest; frontend tests use Vitest with Testing Library. Add or update tests for every behavior change, especially auth, uploads, health pipelines, and report generation. No enforced coverage threshold is configured.

## Commit & Pull Request Guidelines
Recent history follows conventional, imperative subjects such as `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`, and `security: ...`, with optional scopes like `feat(deploy): ...`. Keep each commit focused on one logical change. PRs should summarize impact, list verification commands, note schema or env changes, link the issue when available, and include screenshots for frontend UI work.

## Security & Configuration Tips
Start from `backend/.env.example`, `frontend/.env.example`, and `.env.production.example`; never commit populated `.env` files or secrets. Verify checkpoint placement or `MODEL_CHECKPOINT_PATH` before production runs, and avoid committing generated uploads, reports, or local database artifacts unless they are intentional fixtures.
