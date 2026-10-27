# InvoiceIQ

AI invoice processing and 3-way matching. Upload invoices, purchase orders and receipts.
The AI extracts the data, the app matches the three documents, flags every mismatch with a
reason, and exports only approved records.

> Work in progress. Step 1: project foundations (database, API and web app talking to each other).

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
../../venv/Scripts/python -m uvicorn app.main:app --reload --port 8001

# 4. Web app  (http://localhost:3001), in a second terminal
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
