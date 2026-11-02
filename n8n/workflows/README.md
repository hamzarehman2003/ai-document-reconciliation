# n8n workflows

Workflows for the n8n instance in `docker-compose.yml` (http://localhost:5678), exported as JSON.

| File | What it does |
|---|---|
| `email-intake.json` | New email with PDF attachments → `POST /api/webhooks/inbound` → read by AI and 3-way matched |
| *InvoiceIQ events* (to do) | Webhook `POST /webhook/invoiceiq-events` receives `case.approved` / `case.needs_review` from InvoiceIQ (Header Auth `X-Webhook-Secret`). Still to add: Switch on `event` → Gmail alert / Google Sheets row |

## Import a workflow
1. Start n8n: `docker compose up -d n8n`, then open http://localhost:5678.
2. **Workflows → Import from file**, and pick the JSON file.
3. Create the credentials it needs (they are never stored in these files):
   - **IMAP** (for the email trigger): your Gmail address and a Gmail App password.
   - **Header Auth** named `InvoiceIQ intake key`: name `X-API-Key`, value = `INTAKE_API_KEY` from `.env`.
4. Start the API and the worker, then turn the workflow on (**Active**).
