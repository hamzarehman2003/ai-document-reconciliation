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

## Checks

```bash
venv/Scripts/ruff format services && venv/Scripts/ruff check services
venv/Scripts/python -m pytest
cd apps/web && npm run lint
```
