# Repository Guidelines

## Project Structure & Module Organization
`backend/app/` contains the FastAPI app: routes in `api/`, config and infrastructure in `core/`, ORM models in `models/`, and business logic in `services/`. ECG preprocessing and inference live in `backend/ml/`, and migrations live in `backend/alembic/versions/`. `frontend/src/` contains the React app, organized into `components/`, `pages/`, `auth/`, `api/`, `controllers/`, `utils/`, and `__tests__/`. Repository-level regression tests live in `tests/`. Generated files belong in `data/uploads/`, `data/reports/`, and `models/checkpoints/`; keep source changes out of those paths unless updating fixtures or model placeholders.

## Build, Test, and Development Commands
- `cd backend && uv venv .venv --python 3.11 && uv pip install --python .venv/bin/python -r requirements.txt`: create the backend environment.
- `./start.sh`: start the backend from the repository root.
- `cd backend && .venv/bin/python -m alembic upgrade head`: apply migrations before running against MySQL.
- `cd frontend && npm install && npm run dev`: start the Vite frontend.
- `cd frontend && npm run build`: type-check and build production assets.
- `cd frontend && npm run lint`: run ESLint.
- `./backend/.venv/bin/python -m pytest -q tests backend/tests`: run backend and repo-level Python tests.
- `cd frontend && npm test -- --run` or `npm run test:coverage`: run Vitest once, optionally with coverage output.
- `docker compose up --build`: boot the full stack with MySQL.

## Coding Style & Naming Conventions
Use 4-space indentation in Python and keep imports Black/isort-friendly. Use 2-space indentation in TypeScript/TSX. Name React components with `PascalCase`, hooks with `useCamelCase`, Python modules with `snake_case.py`, and tests with behavior-focused names. Prefer explicit types in TypeScript and type hints in Python. Frontend linting is enforced with ESLint.

## Testing Guidelines
Place backend tests in `backend/tests/` or `tests/` as `test_*.py`. Place frontend tests under `frontend/src/__tests__/` as `*.test.ts` or `*.test.tsx`. No hard coverage threshold is configured; add or update tests for every behavior change, especially around uploads, auth, diagnosis flows, and migrations.

## Commit & Pull Request Guidelines
Recent history uses conventional, imperative subjects such as `feat(deploy): ...`, `fix: ...`, `test: ...`, `security: ...`, and `chore: ...`. Keep commits scoped to one logical change. PRs should summarize impact, list verification commands, note schema or env changes, link the issue when available, and include screenshots for frontend UI work.

## Security & Configuration Tips
Start from `backend/.env.example` and `frontend/.env.example`; never commit populated `.env` files or secrets. Validate `MODEL_CHECKPOINT_PATH` before production runs, and do not commit generated uploads, reports, or local database files.
