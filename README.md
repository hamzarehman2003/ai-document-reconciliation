# InvoiceIQ

AI invoice processing and 3-way matching. Upload invoices, purchase orders and receipts.
The AI extracts the data, the app matches the three documents, flags every mismatch with a
reason, and exports only approved records.

> Work in progress. Done so far: project foundations, demo dataset generator, database tables, upload API,
> background worker, AI extraction.

## API

Interactive docs: http://localhost:8001/docs

| Method | Path | What it does |
|---|---|---|
| POST | `/api/batches` | Upload 1–20 PDF/PNG/JPEG files; each is checked, de-duplicated, stored and queued |
| GET | `/api/batches` | Recent batches with document counts |
| GET | `/api/batches/{id}` | One batch with its documents |
| GET | `/api/documents/{id}` | One document with the data the AI read: type, number, vendor, dates, totals, line items |
| GET | `/api/documents/{id}/file` | The original file |
| POST | `/api/documents/{id}/reprocess` | Process a document again (uses the cache when the file was already read) |
| GET | `/api/jobs?status=…` | Background jobs: queued, running, done or failed, with attempts and last error |

Uploads are processed by a separate **worker** process that takes jobs from a Postgres-backed queue
(`SELECT … FOR UPDATE SKIP LOCKED`), retries temporary failures with backoff (30 s, 60 s, 120 s) and marks
documents as failed with a reason when a file can't be processed. Several workers can run side by side.

**AI extraction:** each page is rendered to an image and sent to Google Gemini (Flash-Lite) together with the
PDF's text layer (scans have none and are read from the image). Gemini must answer in a strict JSON schema;
the answer is validated with Pydantic, amounts are stored as exact decimals, and every result is cached by file
checksum so the same file is never sent twice. The AI only reads. All checks are done by plain Python rules.

## Tech stack
- **Web:** Next.js, TypeScript, Tailwind CSS, shadcn/ui
- **API:** Python, FastAPI, SQLAlchemy
- **Database:** PostgreSQL (Docker)
- **AI:** Google Gemini

## Run locally

Requirements: Python 3.12, Node.js 20+, Docker Desktop.

```bash
# 1. Settings
cp .env.example .env            # then add your GEMINI_API_KEY

# 2. Database
docker compose up -d db

# 3. API  (http://localhost:8001/docs)
python -m venv venv
venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: venv/bin/python
cd services/api
../../venv/Scripts/alembic upgrade head                  # create/update database tables
../../venv/Scripts/python -m uvicorn app.main:app --reload --port 8001

# 4. Worker, in a second terminal (processes uploaded documents)
cd services/api
../../venv/Scripts/python -m app.worker

# 5. Web app  (http://localhost:3001), in a third terminal
cd apps/web
npm install
npm run dev
```

## Demo dataset

The 3-way match demo needs documents that belong together, so we generate them:
fictional purchase orders, goods receipts and invoices with deliberate mistakes
(overbilling, price changes, wrong totals, duplicates...) and a `truth.json` answer key per set.
About 30% of documents are saved as noisy "scans" with no text layer.

```bash
venv/Scripts/python -m scripts.generate_dataset --sets 50 --seed 42
# → data/generated/sets/SET-0001/{PO,GRN,INV}*.pdf + truth.json, and data/generated/manifest.json
```

All companies and documents are fictional.

## Checks

```bash
venv/Scripts/ruff format services scripts && venv/Scripts/ruff check services scripts
venv/Scripts/python -m pytest
cd apps/web && npm run lint
```
