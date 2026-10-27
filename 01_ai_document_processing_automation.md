# Project 1 — AI Invoice Processing & 3-Way Match Automation

**Working name:** InvoiceIQ (rename freely)
**Goal:** A portfolio project that works end to end and looks like a real SaaS product, to show Fiverr and Upwork clients.
**One-line pitch:** "Upload invoices, purchase orders and receipts. AI extracts the data, matches the three documents, flags every mismatch with a reason, and sends only approved records to your spreadsheet or accounting tool."

---

## 1. The business problem

Finance and operations teams at small and mid-sized businesses copy data from PDFs into spreadsheets by hand. They then check whether each invoice matches the purchase order and what was actually delivered (the "3-way match"). This is slow and error-prone, and it lets duplicate payments and overbilling slip through.

Plain OCR or "PDF to Excel" tools only extract text. They don't validate anything, don't compare documents, and don't explain problems.

**This project shows the whole workflow:**
upload → classify → extract → validate → match → human review → export/sync → audit trail.

**Who this demo speaks to:** bookkeeping firms, accounts payable (AP) teams, e-commerce/logistics businesses, procurement teams, automation agencies.

---

## 2. What the finished demo must prove

A client watching a 2–3 minute video should come away thinking:
1. "It reads my messy PDFs and scans correctly."
2. "It catches mistakes I would have missed, and tells me why."
3. "A human stays in control. Nothing is approved silently."
4. "The data ends up where I already work (Sheets, CSV, my tools)."
5. "This person builds production-quality software, not toy scripts."

---

## 3. Scope

### MVP (must ship)
- Upload single files and batches (PDF, PNG, JPG), with type/size validation.
- Classify each file as invoice, purchase order, goods receipt, or unknown.
- Extract header fields and line items into typed schemas.
- Highlight evidence: clicking a field shows where it came from on the page.
- Confidence per field, with a configurable review threshold.
- Deterministic validation (math, dates, required fields, currency).
- 3-way matching invoice ↔ PO ↔ receipt, with configurable tolerances.
- Exception queue with plain-language reasons and severity.
- Reviewer can edit fields, approve, reject, or add notes.
- Duplicate detection (same file checksum, same vendor + invoice number).
- Export of approved records to CSV, JSON and Excel.
- Audit log of every processing and review event.
- Dashboard with KPIs and charts.
- Demo mode: seeded workspace with sample documents and a one-click "Run sample batch".
- Evaluation report produced by a real evaluation script.

### Phase 2 (adds a lot of client appeal, do after MVP)
- **n8n integration:** email inbox → auto-upload; approved records → Google Sheets row; Slack/email alert when a batch needs review.
- Outgoing webhooks on events (`document.processed`, `case.approved`).
- Vendor profiles with historical mismatch rate.
- AI-drafted email to a vendor about a discrepancy (the reviewer edits and sends). This is a small, honest "AI agent" feature.

### Out of scope
Real ERP/QuickBooks/Xero connectors (keep an adapter interface only), multi-tenant billing, every document type in the world. A narrow flow that works reliably beats a broad one that breaks.

---

## 4. User journey (the demo script follows this)
1. Log in, or click **"Explore demo workspace"**.
2. Dashboard shows KPIs from previously processed batches.
3. Drag in three linked documents (invoice + PO + receipt).
4. Each file card shows a live pipeline: Uploaded → Classified → Extracted → Validated → Matched.
5. One case auto-approves; one is flagged "Invoiced qty 120 > received qty 100".
6. Open the flagged case in the **Match Workspace**: three documents side by side, with the mismatched line highlighted.
7. Click a field to see the highlighted box on the PDF. Correct a misread value.
8. Approve with a note. The audit log records it.
9. Export approved records to Excel, or watch them appear in Google Sheets via n8n (phase 2).
10. Finish on the Evaluation page: accuracy, discrepancy recall, cost per document.

---

## 5. UI and UX: make it look like a real product

### Design direction
- Base all components on **shadcn/ui** (Radix + Tailwind). Customize the theme tokens; don't ship the default look unchanged.
- **Style:** a calm "finance-grade" look. Neutral zinc/slate base, one confident accent (e.g. emerald or indigo), and clear status colors: green = matched, amber = needs review, red = mismatch.
- **Typography:** Geist or Inter for UI, a monospace font (Geist Mono / JetBrains Mono) for amounts, IDs and invoice numbers. Use tabular numbers throughout.
- **Polish:** dark and light mode, skeleton loaders, designed empty states, Sonner toasts, subtle Motion animations (pipeline steps, card entry), a ⌘K command palette, and keyboard shortcuts in review (`J/K` next/prev, `A` approve, `R` reject, `E` edit).
- **Responsive:** the sidebar collapses on tablets, and review screens stay usable at laptop width.
- **Avoid:** generic purple gradients, emoji-heavy UI, lorem ipsum. All demo data should look realistic.

### Screens

| Screen | What it shows | Key shadcn/ui components |
|---|---|---|
| **Login / Landing** | Product pitch, animated pipeline illustration, "Explore demo" button | Card, Button, Input, Form |
| **Dashboard** | KPI cards (docs processed, auto-approval %, open exceptions, hours saved, cost/doc); volume area chart; status donut; top discrepancy types; recent activity | Card, Chart (Recharts), Badge, Avatar, Tabs |
| **Upload / Batches** | Large dropzone; one card per file with a live pipeline stepper and progress; batch summary | Card, Progress, Badge, Tooltip, Alert |
| **Documents** | Data table with faceted filters (status, type, vendor, date), search, column toggles, row actions | Data Table (TanStack), DropdownMenu, Popover, Calendar, Command |
| **Document Detail ("Evidence View")** | Resizable split view: PDF viewer with confidence-colored bounding boxes on the left; extracted fields form on the right; hovering a field highlights its box; tabs for Fields / Line items / Raw text / History | ResizablePanelGroup, Tabs, Form, Input, Badge, ScrollArea, HoverCard |
| **Match Workspace (signature screen)** | Three columns (Invoice / PO / Receipt) with line items aligned row by row; mismatched cells in red with the reason in a tooltip; match score; Approve / Reject / Request info | Table, Tooltip, Badge, Dialog, Textarea, Separator |
| **Exception Queue** | Table or Kanban (Needs review → In progress → Resolved), with severity, age and assignee | Data Table, Tabs, Badge, Sheet, Select |
| **Vendors** *(phase 2)* | Vendor profile, document history, mismatch rate | Card, Table, Chart |
| **Rules & Settings** | Tolerance sliders (qty %, price %, rounding), rule on/off toggles, review confidence threshold, LLM provider/model | Slider, Switch, Select, Form, Card |
| **Exports** | New export dialog (format, filters), export history, download | Dialog, RadioGroup, Table |
| **Audit Log** | Timeline of who did what, filterable | Table, Badge, Calendar |
| **Evaluation** | Metrics from the last eval run: per-field accuracy chart, classification confusion matrix, discrepancy precision/recall, latency, cost | Card, Chart, Table |

**Supporting frontend libraries:** TanStack Query (server state), TanStack Table, react-hook-form + zod, react-pdf (pdf.js) for the viewer, react-dropzone, next-themes, lucide-react, Motion.

---

## 6. Extraction pipeline

1. **Ingest:** store the original file, compute a SHA-256 checksum, and short-circuit if it is a duplicate.
2. **Pre-process with PyMuPDF:** pull the text layer plus word-level bounding boxes, and render each page to an image.
3. **OCR fallback for scans:** if a page has no usable text layer, run RapidOCR (CPU, ONNX) or Tesseract to get words and boxes.
4. **Classify:** a cheap LLM call or keyword heuristics → invoice / PO / receipt / unknown.
5. **Extract with a vision LLM:** send the page image and the text/OCR words. Get back JSON that matches a Pydantic schema via structured outputs. Validate it again on the server; output that fails validation becomes "needs review", never silently accepted.
6. **Locate evidence:** fuzzy-match each extracted value against the word boxes to find its page and bounding box. That gives you the click-to-highlight feature without trusting LLM-generated coordinates.
7. **Score confidence:** combine signals (schema-valid, evidence found, OCR confidence, validation passes) into a 0–1 score per field.
8. **Validate and match:** run plain, unit-tested Python rules (section 7). There is no LLM in this step.

Keep the LLM and OCR behind adapter interfaces: `LLMProvider` (anthropic, mock/replay, optional others) and `OCRProvider` (rapidocr, tesseract).

---

## 7. Validation and matching rules

Each rule returns `{code, status, severity, message, evidence}`, for example
`QTY_EXCEEDS_RECEIVED · error · "Invoiced 120 units of SKU-4471 but only 100 were received (tolerance 5%)."`

- Required fields present (vendor, invoice number, date, total).
- Line totals = qty × unit price (rounding tolerance).
- Subtotal + tax − discount = total (currency tolerance).
- Dates valid, invoice date not in the future, due date ≥ invoice date.
- Invoice references an existing PO.
- Invoice vendor = PO vendor (normalized name/ID).
- Invoiced qty ≤ received qty + tolerance.
- Invoice unit price = PO unit price ± tolerance.
- Duplicate vendor + invoice number flagged.
- Any field below the confidence threshold → review.

At least 8 rules, each with unit tests covering pass, fail and edge cases.

---

## 8. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js (App Router), React, TypeScript, Tailwind CSS, shadcn/ui | Industry standard, looks production-grade |
| Backend API | Python, FastAPI, Pydantic v2 | Typed, fast, auto OpenAPI docs |
| Database | PostgreSQL, SQLAlchemy 2, Alembic | Real migrations, relational data |
| Background jobs | Separate worker process using a Postgres job table (`SELECT … FOR UPDATE SKIP LOCKED`) | No Redis/Celery needed; simpler to deploy, still shows proper async design |
| Live updates | Server-Sent Events (SSE) from the API | Live pipeline progress in the UI |
| PDF | PyMuPDF | Text, word boxes, page rendering |
| OCR | RapidOCR or Tesseract (CPU) | Free, no GPU |
| LLM | Anthropic Claude via official SDK, structured outputs; model configurable | Vision + reliable JSON |
| File storage | Local volume in dev; S3-compatible (MinIO in Docker, Cloudflare R2 in prod) | Real storage abstraction |
| Auth | Email/password + JWT httpOnly cookie, roles `admin` / `reviewer` | Enough for a convincing demo |
| Automation (phase 2) | n8n (self-hosted in Docker Compose) | What clients actually ask for |
| Testing | pytest (unit, API, rules), Playwright (critical UI flows) | Shows engineering discipline |
| CI | GitHub Actions: lint, type-check, tests | Green badge in README |
| Packaging | Docker + Docker Compose | One command to run everything |

No vector database and no RAG. This is structured extraction plus reconciliation.

---

## 9. Architecture

```text
[Next.js web] ──HTTP/SSE──> [FastAPI API] ──> [PostgreSQL]
                                 │                 ▲
                                 ▼                 │
                          [Object storage]   [Worker process]
                                                 │   ├─ PyMuPDF / OCR
                                                 │   ├─ LLM provider adapter
                                                 │   └─ Rules + matching engine
                                                 ▼
                                          [n8n] (phase 2: email in, Sheets/Slack out)
```

---

## 10. Data model
- `User` (role)
- `Batch` (status, counts)
- `Document` (type, storage key, checksum, status, page count, vendor_id)
- `Page` (number, has_text_layer, image key)
- `ProcessingRun` (provider, model, tokens, cost, latency, error code)
- `ExtractedField` (name, value, normalized value, confidence, page, bbox, source text, corrected_by)
- `LineItem` (sku, description, qty, unit price, total)
- `Vendor` (name, normalized name, tax ID)
- `MatchCase` (invoice_id, po_id, receipt_id, status, score)
- `Discrepancy` (case_id, rule code, severity, message, evidence)
- `ReviewAction` (reviewer, decision, edits, note)
- `AuditEvent` (actor, action, object, metadata, timestamp)
- `ExportJob` (format, filters, status, file key)
- `Job` (queue table: type, payload, status, attempts, run_after)

---

## 11. API outline
- `POST /api/auth/login`, `POST /api/auth/demo`
- `POST /api/batches` · `GET /api/batches/{id}` · `GET /api/batches/{id}/events` (SSE)
- `POST /api/documents` · `GET /api/documents` · `GET /api/documents/{id}` · `GET /api/documents/{id}/file`
- `PATCH /api/documents/{id}/fields` (corrections)
- `GET /api/cases` · `GET /api/cases/{id}` · `POST /api/cases/{id}/decision`
- `GET/PUT /api/settings/rules`
- `POST /api/exports` · `GET /api/exports/{id}/download`
- `GET /api/audit-events`
- `GET /api/metrics/dashboard` · `GET /api/metrics/evaluation`
- `POST /api/webhooks/inbound` (phase 2, used by n8n)

---

## 12. Synthetic dataset and evaluation

**Generate the dataset yourself (free, and the labels come for free too):**
- A Python script using Faker + HTML templates → PDF (WeasyPrint or ReportLab).
- 5–8 visually different vendor templates (layouts, fonts, logos, currencies).
- For every PO, generate a matching receipt and invoice, then inject known errors: quantity overbilling, price changes, wrong totals, duplicate invoice numbers, missing PO reference, unknown vendor.
- Make "scanned" copies by rasterizing pages and adding noise, blur, rotation and skew (Pillow or Augraphy).
- Save ground-truth JSON next to every document.
- Target: about 150 documents (about 50 linked sets), with a held-out test split.

**`make eval` measures:**
- Field-level exact and normalized accuracy.
- Classification precision, recall and F1.
- Discrepancy detection precision, recall and F1 (recall on serious errors matters most).
- Share of documents that need human review.
- Median and p95 latency per document.
- Actual cost per document (from token usage).

The Evaluation page and README show only numbers from real runs.

---

## 13. Demo mode and cost safety (important for a public portfolio link)
- The seeded demo workspace uses **pre-processed results** (cached by file checksum), so visitors clicking around costs $0.
- "Run sample batch" replays cached LLM responses through the real pipeline, so it looks live and costs nothing.
- Uploading your own files in the public demo is rate-limited (e.g. 5 files per visitor per day) and capped by a monthly spend limit in the API console.
- A `mock` LLM provider is used for tests and CI.
- The demo workspace resets nightly.

---

## 14. Repository structure
```text
invoiceiq/
  apps/web/                 # Next.js + shadcn/ui
  services/api/             # FastAPI app
  services/worker/          # job runner: parse, OCR, extract, match
  packages/rules/           # pure-Python validation & matching (no I/O)
  packages/schemas/         # Pydantic models (+ generated TS types for web)
  scripts/generate_dataset/ # synthetic document generator
  data/samples/             # demo documents + ground truth
  tests/{unit,integration,e2e,evaluation}/
  n8n/workflows/            # exported workflow JSON (phase 2)
  docs/{architecture.md, screenshots/}
  docker-compose.yml
  .env.example
  README.md
```

---

## 15. Build plan (solo; about 3–4 weeks part-time, 2 weeks full-time)

| Phase | Deliverable |
|---|---|
| 1. Foundations | Repo, Docker Compose, DB schema + migrations, auth, shadcn theme + app shell (sidebar, header, ⌘K, dark mode) |
| 2. Dataset | Synthetic generator, 150 docs with ground truth |
| 3. Pipeline | Upload, job queue, PyMuPDF + OCR, LLM extraction with schema validation, evidence boxes |
| 4. Rules | Validation + 3-way match engine with unit tests |
| 5. Review UI | Documents table, Evidence View, Match Workspace, Exception Queue, decisions + audit |
| 6. Outputs | Exports (CSV/JSON/XLSX), Dashboard charts, Settings |
| 7. Quality | Eval script + Evaluation page, Playwright tests, CI, demo mode/caching |
| 8. Ship | Deploy, README, screenshots, 2–3 min demo video |
| 9. Phase 2 | n8n email → upload, approved → Google Sheets, Slack alert, vendor email draft |

---

## 16. Acceptance criteria
- [ ] `docker compose up` starts web, API, worker, DB and storage with no manual steps.
- [ ] Single and batch upload work, with live per-file progress.
- [ ] Digital PDFs and noisy scans both extract; invalid output goes to review, never auto-approved.
- [ ] Clicking a field highlights its source on the PDF.
- [ ] At least 8 rules, each unit-tested; every discrepancy shows a code, severity and plain-language reason.
- [ ] Match Workspace shows invoice/PO/receipt side by side with highlighted mismatches.
- [ ] Reviewer edits and decisions appear in the audit log.
- [ ] Only approved records are exported.
- [ ] Duplicate uploads and job retries are safe (tested).
- [ ] Evaluation script runs and the Evaluation page shows its real output.
- [ ] Public demo runs at $0 per visitor via cached results.
- [ ] Lighthouse score ≥ 90 on Dashboard; no layout breaks at 1280px and 768px.
- [ ] README: problem, demo video/GIF, screenshots, architecture diagram, setup, API docs link, evaluation results, limitations.

---

## 17. Running costs: paid APIs, GPU, hosting

**GPU: not needed.** PDF parsing and OCR (RapidOCR/Tesseract) run fine on a normal CPU. The heavy AI work happens on the LLM provider's servers.

**LLM API: paid, but very cheap.** Rough estimate per invoice page, assuming about 3K input tokens (image + text) and about 1K output tokens:

| Model | Price (input / output per 1M tokens) | ≈ Cost per page | ≈ 150-doc eval run |
|---|---|---|---|
| Claude Haiku 5.5 | $0.10 / $0.50 | ~$0.001 | ~$0.15 |
| Claude Sonnet 5.5 | $2 / $10 | ~$0.016 | ~$2.40 |
| Claude Opus 5.5 | $4 / $20 | ~$0.032 | ~$4.80 |

- Keep the model configurable. Run the eval on each and show the accuracy vs. cost table in the README; clients love that.
- A $5–10 API credit covers development, many eval runs and the public demo (thanks to caching).
- **Free alternatives:** local vision models via Ollama (free, but slow on CPU and less accurate), or providers that offer a free tier (check current limits and data-usage terms).

**Hosting:**
- Simplest option: one small VPS (about $5/month) running the whole Docker Compose stack.
- Free-tier option: Vercel (web) + Neon (Postgres) + Cloudflare R2 (files) + Render/Fly/Railway (API + worker). Free backends may sleep after inactivity, so the first load is slow.
- Domain (optional): about $10/year.

**Everything else is free:** shadcn/ui, Next.js, FastAPI, Postgres, PyMuPDF, RapidOCR/Tesseract, n8n (self-hosted), GitHub Actions, Playwright.

**Realistic total:** about $5–15 to build, then $0–5/month to keep the demo live.

---

## 18. Packaging it for Fiverr and Upwork
- **Demo video (2–3 min):** follow the user journey in section 4. Lead with the problem, end with the evaluation numbers.
- **Live demo link** with "Explore demo workspace" (no signup).
- **README / case study:** Problem → Approach → Results (real metrics) → Stack → Screenshots.
- **Upwork portfolio entry:** written as a client case study, with an ROI line such as "reduces manual entry from ~4 min to ~30 sec per invoice" (measure it during the demo; don't invent it).
- **Fiverr gig packages this project supports:**
  - *Basic:* extract one document type → CSV/Excel/Google Sheets.
  - *Standard:* multiple document types + validation rules + n8n/Zapier/Make automation.
  - *Premium:* full extraction + 3-way matching + review dashboard + deployment.
- Offer ERP/accounting integrations (QuickBooks, Xero, etc.) as custom-scoped orders.
