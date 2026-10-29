# InvoiceIQ

AI invoice processing and 3-way matching. Upload invoices, purchase orders and receipts.
The AI extracts the data, the app matches the three documents, flags every mismatch with a
reason, and exports only approved records.

> Work in progress. Done so far: project foundations, demo dataset generator, database tables, upload API,
> background worker, AI extraction, OCR + click-to-highlight evidence, 3-way matching, simple upload page.

## API

Interactive docs: http://localhost:8001/docs

| Method | Path | What it does |
|---|---|---|
| POST | `/api/batches` | Upload 1–20 PDF/PNG/JPEG files; each is checked, de-duplicated, stored and queued |
| GET | `/api/batches` | Recent batches with document counts |
| GET | `/api/batches/{id}` | One batch with its documents |
| GET | `/api/documents/{id}` | One document with the data the AI read (type, number, vendor, dates, totals, line items) and where each value is on the page |
| GET | `/api/documents/{id}/file` | The original file |
| GET | `/api/documents/{id}/pages/{n}` | One page as an image, for the page viewer |
| POST | `/api/documents/{id}/reprocess` | Process a document again (uses the cache when the file was already read) |
| GET | `/api/jobs?status=…` | Background jobs: queued, running, done or failed, with attempts and last error |
| GET | `/api/match-cases?status=…&invoice_id=…` | 3-way match cases (one per invoice) with the problems found |
| GET | `/api/match-cases/{id}` | One case with its invoice, purchase order and goods receipt |
| POST | `/api/match-cases/refresh` | Check every invoice again (after changing rules or tolerances) |

Uploads are processed by a separate **worker** process that takes jobs from a Postgres-backed queue
(`SELECT … FOR UPDATE SKIP LOCKED`), retries temporary failures with backoff (30 s, 60 s, 120 s) and marks
documents as failed with a reason when a file can't be processed. Several workers can run side by side.

**AI extraction:** each page is rendered to an image and sent to Google Gemini (Flash-Lite) together with the
PDF's text layer (scans have none and are read from the image). Gemini must answer in a strict JSON schema;
the answer is validated with Pydantic, amounts are stored as exact decimals, and every result is cached by file
checksum so the same file is never sent twice. The AI only reads. All checks are done by plain Python rules.

**Evidence (click-to-highlight):** every extracted value is located on the page, using the PDF's own words for
digital documents and **RapidOCR** (CPU, offline) for scans and photos. Each value is searched in all common
formats (`30706.76` → `€30,706.76` or `30.706,76 €`), and line-item values only within their own table row.
In the app, clicking a value highlights it on the page; values that can't be found are flagged for checking.

**3-way matching:** each invoice is linked to its purchase order (by PO number) and goods receipt, in any upload
order, and checked by plain Python rules (no AI): quantity billed vs received, price vs PO, items not on the PO,
line and invoice arithmetic, missing PO reference, vendor mismatch and duplicate invoices (deliveries split over
several goods receipts are added up). Matching runs as its own background job under a database lock, so documents
can be processed by several workers at once and in any order. Every problem is
explained in plain words ("CPF-15: billed 10, but only 8 received") and linked to the values on the page.
The rules are tested against 300 generated document sets, each of which must get exactly its injected mistake.

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
