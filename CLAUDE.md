# CLAUDE.md

## Project
AI invoice processing and 3-way match (invoice ↔ purchase order ↔ receipt) web app.
It is a portfolio demo for Fiverr/Upwork, recorded as a video. It is not a client production system.
The full spec is in `01_ai_document_processing_automation.md`. Follow it, but keep the demo scope small.

## How we work
- The user is learning. Claude writes all the code; the user reviews and asks questions.
- Build one small step at a time. Propose a short plan first, wait for approval, then implement.
- After each step, explain briefly what was built, which files changed, and how to run or see it.
- Prefer simple, readable code over clever code. No features beyond the current step.
- Ask before adding a new dependency, service or major structural change.

## Python code style
- Follow PEP 8. Format with `ruff format` and lint with `ruff check`.
- API structure: `app/main.py` only creates the app and includes routers. Each route group has
  its own file in `app/routes/` (e.g. `routes/health.py`) with an `APIRouter` named `router`.
- Layers: `routes/` (thin: read request, call a service, return a schema) → `services/` (business logic,
  no HTTP) → `models/` (database). Response shapes live in `schemas/`. Files go through `storage.py`.
- Routes get the database and storage via `SessionDep` (`app/db.py`) and `StorageDep` (`app/storage.py`).
- Routes that use the database are plain `def` (not `async def`), because SQLAlchemy sessions are synchronous.
- Background work: add a handler in `app/services/`, register it in `HANDLERS` in `app/worker.py`, and queue it
  with a `Job(kind=..., payload=...)`. Raise `PermanentJobError` for errors that retrying can't fix;
  any other exception is retried with backoff (`app/services/job_queue.py`).
- Worker tests use the `empty_queue` fixture (`tests/test_worker.py`) to hide jobs from the dev database.
- Type hints on all functions. Use Pydantic models for data shapes.
- Small functions with clear names. Short docstrings on public functions and modules only.
- Validation and matching rules are plain Python with no I/O and no LLM calls, each with pytest tests.

## Database
- SQLAlchemy 2 typed models in `app/models/` (one file per table, all imported in `app/models/__init__.py`).
- Every schema change is a new Alembic migration in `services/api/alembic/versions/`. Never edit a migration
  that has already been applied; add a new one instead.
- The database grows step by step: only add tables when a step actually needs them.
- Status/type columns use `text_enum()` from `app/models/base.py` (stored as text, not Postgres enums).
- Shared test fixtures are in `services/api/tests/conftest.py`: `session` (rolled back after each test),
  `storage` (temporary folder), `client` (API client using both), `make_pdf` (unique small PDF).

## Python environment
- Use the existing virtual environment in `venv/` (repo root). Do not create another one.
- Every Python package goes in the root `requirements.txt` with a pinned version.
  When a step adds a package, update `requirements.txt` and install it:
  `venv/Scripts/python -m pip install -r requirements.txt`.

## Commands
- Database: `docker compose up -d db`, then from `services/api`: `../../venv/Scripts/alembic upgrade head`
- New migration (from `services/api`): `../../venv/Scripts/alembic revision --autogenerate --rev-id 0002 -m "what changed"`
  (next free number), then review the generated file and run `alembic check`.
- API: from `services/api`, `../../venv/Scripts/python -m uvicorn app.main:app --reload --port 8001`
- Worker (separate process, needed for uploads to be processed): from `services/api`,
  `../../venv/Scripts/python -m app.worker` (add `--once` to process what's waiting and exit)
- Web: from `apps/web`, `npm run dev` (port 3001; `/api/*` is forwarded to the API on 8001)
- Ports 3000 and 8000 are taken by the user's other Docker project (Grafana, inference API). Don't use them.
- Demo dataset: `venv/Scripts/python -m scripts.generate_dataset --sets 50 --seed 42` → `data/generated/` (git-ignored)
- Python checks: `venv/Scripts/ruff format services scripts`, `venv/Scripts/ruff check services scripts`, `venv/Scripts/python -m pytest`
- Web checks: from `apps/web`, `npm run lint` and `npx tsc --noEmit`

## Frontend code style
- Next.js 16 has breaking changes. Read `apps/web/AGENTS.md` and the guides in
  `apps/web/node_modules/next/dist/docs/` before writing frontend code.
- Next.js (App Router) + TypeScript + Tailwind + shadcn/ui components.
- Use shadcn/ui components before writing custom ones. Keep components small.
- No `any` types. Use realistic demo data, never lorem ipsum.

## Stack (from spec)
- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL; a worker process using a Postgres job table (no Redis/Celery).
- PDF: PyMuPDF. OCR fallback: RapidOCR or Tesseract (CPU only).
- LLM: Google Gemini free tier. Default model `gemini-flash-lite-latest`; optional retry with `gemini-flash-latest`.
  Keep it behind an `LLMProvider` adapter, retry on 503/429, and cache results by file checksum so quota is not reused.
- Docker Compose runs everything locally.

## Secrets and data
- API key is in `.env` as `GEMINI_API_KEY`. Never print it, log it, commit it or hard-code it.
- `data/raw/` holds downloaded datasets (Northwind invoice PDFs, SROIE and CORD receipts). It is git-ignored; never commit it.
- `data/generated/` is created by the dataset generator (linked PO/receipt/invoice sets + `truth.json`).
  Scenario codes in `scripts/generate_dataset/models.py` (`Scenario`) are the same codes the matching rules must return.
- Commit only small sample files and generated demo data that are needed by the app.

## Git
- Remote: `github.com/hamzarehman2003/ai-document-reconciliation`, branch `main`.
- This repo uses the user's personal git identity (set locally). Do not change git config.
- Commit or push only when the user asks. Small commits, one per working step.
