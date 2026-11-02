# n8n workflows

Workflows for the n8n instance in `docker-compose.yml` (http://localhost:5678), exported as JSON.

| File | What it does |
|---|---|
| `email-intake.json` | New email with PDF attachments → `POST /api/webhooks/inbound` → read by AI and 3-way matched |
| `invoiceiq-events.json` | InvoiceIQ sends `case.approved` / `case.needs_review` to the Webhook node → Switch on `event` → approved: a row in Google Sheets; needs review: an alert email |

## Import a workflow
1. Start n8n: `docker compose up -d n8n`, then open http://localhost:5678.
2. **Workflows → Import from file**, and pick the JSON file.
3. Create the credentials it needs (they are never stored in these files):

| Credential | Used by | Values |
|---|---|---|
| **IMAP** | Email intake trigger | Gmail address + Gmail App password, `imap.gmail.com`, port 993, SSL |
| **Header Auth** `InvoiceIQ intake key` | Email intake → HTTP Request | name `X-API-Key`, value = `INTAKE_API_KEY` from `.env` |
| **Header Auth** `InvoiceIQ webhook secret` | Events → Webhook | name `X-Webhook-Secret`, value = `WEBHOOK_SECRET` from `.env` |
| **SMTP** | Events → alert email | Gmail address + App password, `smtp.gmail.com`, port 465, SSL |
| **Google Service Account** | Events → Google Sheets | service account email + `private_key` from its JSON key file |

4. In `invoiceiq-events.json`, replace the placeholders: the email addresses in **Send an Email**, and in
   **Append row in sheet** pick your own sheet (shared with the service account as Editor). The sheet's
   first row: `Approved at, Invoice, Vendor, Invoice date, Currency, Total, PO number, Approved by, Note`.
5. Start the API and the worker, then **Save** and **Publish** the workflow. In n8n, edits are a draft until
   you publish again.
