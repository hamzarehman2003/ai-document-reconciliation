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

## AI extraction
- Everything that talks to an AI model lives in `app/llm/`. The rest of the app only calls
  `get_extractor().extract(PreparedDocument)` and gets an `ExtractionResult` back.
- The JSON shape the model must return is `app/llm/schema.py`; the instruction is `app/llm/prompt.py`.
  Bump `PROMPT_VERSION` when either changes (old cached results are then ignored).
- The AI only reads. All checks (totals, matching) are plain Python rules.
- Results are cached in `extractions` by file checksum + prompt version: never call Gemini twice for one file.
- Tests never call the real API: the autouse `fake_extractor` fixture (`tests/fakes.py`) replaces it.
- Gemini errors: 408/429/5xx and network problems → normal exception (retried); other API errors and a
  missing key → `PermanentExtractionError` (document fails with a clear message).

## Evidence (where each value is on the page)
- `app/services/page_text.py` reads every word with its box: PDF text for digital pages, RapidOCR
  (`app/services/ocr.py`, CPU, models bundled in the package) for scans and photos. Gemini's input does not change.
- `app/services/evidence.py` searches each extracted value in all common formats and saves `field_evidence`
  rows (boxes as 0-1 fractions of the page). Line-item values are searched only in their SKU's row.
- Evidence is a bonus: if reading words fails, the document is still processed (no evidence).
- Field names: header fields as on `Document` (`total`), line items as `line_items.<position>.<field>`.

## 3-way matching
- Rules live in `app/rules/` and are pure: plain dataclasses in (`DocumentData`), `Finding`s out. No database,
  no AI. One function per rule in `checks.py`; `check_invoice()` runs them all.
- Rule codes (`app/rules/types.py` `Code`) must stay in sync with the generator's `Scenario` codes.
  `tests/test_rules.py` checks the rules against 300 generated sets: every set must get exactly its codes.
- `app/services/matching.py` links invoice → PO (by PO number) → all receipts (by the PO number they reference;
  quantities of several receipts are added up), runs the rules and saves one `MatchCase` per invoice with its
  `Discrepancy` rows.
- Matching is its own job (`match_document`), queued in the same commit that marks a document processed or failed.
  It takes `lock_matching()` (a Postgres advisory lock), so only one matching runs at a time; anything else that
  matches (e.g. `/refresh`) must take the same lock. A matching error is retried on its own and never fails the document.
- A change to a document re-checks: invoices with the same number (duplicates, in any order), invoices referring to
  its PO number, and every case that points at it (as PO, receipt, or in a problem's `refs`).
- `MatchCase.waiting_for` lists missing documents even when the status is `needs_review`.

## Human review and audit log
- `MatchCase.status` is what the rules found; `review_status` is the person's decision (pending/approved/rejected),
  made via `app/services/review.py` `decide()`. Approving needs PO + receipt; a note is required to reject or to
  approve a case with problems. If a re-check changes the result after a decision, it is reset to pending.
- Corrections go through `app/services/corrections.py` `correct_field()` (typed, validated) and are stored in
  `field_corrections`; `reapply_corrections()` puts them back after every new AI read. A correction queues a re-match.
- Every user or system action writes an `AuditEvent` with `app/services/audit.py` `record()`, in the same transaction
  as the action. No login yet: the reviewer's name comes with the request (default "Demo reviewer").
- Shared test helpers: `tests/factories.py` (`add_document`, `add_three_way_set`); fixtures `empty_queue`, `run_jobs`.

## Export and dashboard
- `app/services/export.py`: only approved cases are exported; Excel via openpyxl (columns defined once in
  `INVOICE_COLUMNS` / `LINE_COLUMNS`), CSV as UTF-8 with BOM. Each export writes a `case_exported` audit event.
- `app/services/dashboard.py`: every number is a SQL aggregate (count/sum/group by), never a Python loop over rows.
  Money is always grouped per currency, never added across currencies.
- Dashboard tests compare numbers before and after adding known data, because the dev database isn't empty.

## Evaluation
- `python -m app.evaluation` (from services/api) runs the real pipeline on the generated `test` split, scores it
  against `truth.json` and writes `docs/evaluation.md` (committed) and `data/eval/results.json` (git-ignored).
- Gemini answers are cached in `data/eval/cache/` and reused from the `extractions` table, so re-runs are free;
  `--no-ai` uses cached answers only.
- Never quote accuracy numbers anywhere (README, video, messages) that aren't in the latest `docs/evaluation.md`.
- Tolerances are settings (`price_tolerance_percent`, `quantity_tolerance_percent`, `amount_tolerance`).
  After changing rules or tolerances: `POST /api/match-cases/refresh`.
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
- Accuracy report: from `services/api`, `../../venv/Scripts/python -m app.evaluation` → `docs/evaluation.md`
- Python checks: `venv/Scripts/ruff format services scripts`, `venv/Scripts/ruff check services scripts`, `venv/Scripts/python -m pytest`
- Web checks: from `apps/web`, `npm run lint` and `npx tsc --noEmit`

## Frontend code style
- Next.js 16 has breaking changes. Read `apps/web/AGENTS.md` and the guides in
  `apps/web/node_modules/next/dist/docs/` before writing frontend code.
- Next.js (App Router) + TypeScript + Tailwind + shadcn/ui components.
- Use shadcn/ui components before writing custom ones. Keep components small.
- No `any` types. Use realistic demo data, never lorem ipsum.
- Data is loaded in client components through `src/lib/api.ts` (relative `/api/*` URLs); pages stay
  server components with `metadata`. With `cacheComponents`, anything that reads `usePathname()`/`params`
  must sit inside `<Suspense>`, or routes with an id in the URL fail to build (see `app-sidebar.tsx`).
- Charts: shadcn `chart` (recharts), colours from the `--chart-*` tokens. One series per chart unless a
  palette passes the dataviz validator.

## Design system ("Ledger")
- Colours are tokens in `apps/web/src/app/globals.css` (light `:root` and `.dark`). Never hard-code
  Tailwind palette colours (emerald, amber, sky…); use `primary`, `success`, `warning`, `destructive`,
  `muted`, `accent`.
- Fonts: `font-heading` (Fraunces) only for page titles and big numbers; Plex Sans for UI;
  `numeric` utility (Plex Mono, tabular) for amounts, IDs, SKUs and dates. `eyebrow` for small-caps labels.
- Pages live in `src/app/(app)/` (shared sidebar + header shell); new pages also go in `src/lib/navigation.ts`.
- Every page starts with `PageHeader`. Statuses use `Stamp` / `status-stamps.tsx` (not `Badge`), key numbers
  use `StatTile`, empty lists use `EmptyState` (all in `src/components/ledger/`).
- `/design` shows every component; add new shared components there.

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
