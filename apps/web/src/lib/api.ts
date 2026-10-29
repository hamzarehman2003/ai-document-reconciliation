// Types and calls for the backend API. Requests go to /api/*, which
// next.config.ts forwards to FastAPI. Money arrives as strings ("1234.50").

export type DocumentStatus = "uploaded" | "processing" | "processed" | "failed";
export type DocumentType = "unknown" | "invoice" | "purchase_order" | "goods_receipt";

export type DocumentSummary = {
  id: number;
  filename: string;
  status: DocumentStatus;
  doc_type: DocumentType;
  error_message: string | null;
};

export type LineItem = {
  position: number;
  sku: string | null;
  description: string;
  quantity: string | null;
  quantity_ordered: string | null;
  unit_price: string | null;
  line_total: string | null;
};

/** Where a value was found: page and box as fractions (0-1) of the page size. */
export type Evidence = {
  field: string; // "total", "line_items.3.unit_price", ...
  page: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  text: string;
  source: "pdf_text" | "ocr";
  confidence: number | null;
};

export type DocumentDetail = DocumentSummary & {
  page_count: number | null;
  document_number: string | null;
  vendor_name: string | null;
  buyer_name: string | null;
  issue_date: string | null;
  due_date: string | null;
  po_reference: string | null;
  currency: string | null;
  subtotal: string | null;
  tax: string | null;
  total: string | null;
  line_items: LineItem[];
  latest_extraction: {
    model: string;
    input_tokens: number | null;
    output_tokens: number | null;
    duration_ms: number | null;
  } | null;
  evidence: Evidence[];
  corrections: Correction[];
};

/** A value a person corrected. The latest one per field is in effect. */
export type Correction = {
  field: string;
  old_value: string | null;
  new_value: string | null;
  corrected_by: string;
  note: string | null;
  created_at: string;
};

export type BatchDetail = {
  id: number;
  name: string;
  documents: DocumentSummary[];
};

export type UploadResult = {
  filename: string;
  outcome: "accepted" | "duplicate" | "rejected";
  document_id: number | null;
  existing_document_id: number | null;
  detail: string | null;
};

export type UploadResponse = {
  batch: BatchDetail | null;
  results: UploadResult[];
};

/** Upload files. A 400 "nothing accepted" still returns the per-file results. */
export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  const response = await fetch("/api/batches", { method: "POST", body: form });
  const body = await response.json();

  if (response.ok) {
    return body as UploadResponse;
  }
  if (response.status === 400 && body.detail?.results) {
    return { batch: null, results: body.detail.results as UploadResult[] };
  }
  throw new Error(
    typeof body.detail === "string" ? body.detail : "Upload failed. Is the API running?",
  );
}

export type MatchStatus = "matched" | "needs_review" | "waiting";

export type Discrepancy = {
  code: string;
  severity: "error" | "warning";
  message: string;
  details: Record<string, string>;
  refs: { document_id: number | null; field: string }[];
};

export type MatchCase = {
  id: number;
  status: MatchStatus;
  invoice_id: number;
  invoice_number: string | null;
  vendor_name: string | null;
  invoice_date: string | null;
  currency: string | null;
  total: string | null;
  po_number: string | null;
  purchase_order_id: number | null;
  goods_receipt_ids: number[];
  /** Still missing for a full check, even when problems were already found. */
  waiting_for: ("purchase_order" | "goods_receipt")[];
  review_status: "pending" | "approved" | "rejected";
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  updated_at: string;
  discrepancies: Discrepancy[];
};

/** An amount in one currency: currencies are never added together. */
export type AmountByCurrency = {
  currency: string;
  amount: string;
  invoices: number;
};

export type Dashboard = {
  documents: {
    total: number;
    processed: number;
    failed: number;
    in_progress: number;
    by_type: Partial<Record<DocumentType, number>>;
  };
  invoices: {
    total: number;
    by_match_status: Partial<Record<MatchStatus, number>>;
    by_review_status: Partial<Record<MatchCase["review_status"], number>>;
    /** Matched ÷ (matched + needs review), or null before the first check. */
    match_rate: number | null;
  };
  money_at_risk: AmountByCurrency[];
  approved_amount: AmountByCurrency[];
  top_problems: { code: string; count: number }[];
  ai: {
    documents_read: number;
    average_seconds: number | null;
    input_tokens: number;
    output_tokens: number;
  };
  corrections: number;
  /** The last 14 days, oldest first, zeros included. */
  daily: { day: string; uploaded: number; approved: number }[];
};

export type AuditEvent = {
  id: number;
  created_at: string;
  actor: string;
  action: string; // "document_uploaded", "case_approved", ...
  object_type: "document" | "match_case";
  object_id: number;
  details: Record<string, unknown>;
  /** "CPF-84364 · Cedar & Pine Furniture" or the file name; null if it no longer exists. */
  subject: string | null;
  /** The document to open for this event (for a match case: its invoice). */
  document_id: number | null;
};

/** A document in the list: what the AI read, without line items. */
export type DocumentRow = DocumentSummary & {
  document_number: string | null;
  vendor_name: string | null;
  issue_date: string | null;
  currency: string | null;
  total: string | null;
  created_at: string;
};

/** Approve (OK to pay), reject, or reopen. Throws the API's explanation if refused. */
export async function decideMatchCase(
  caseId: number,
  decision: "approve" | "reject" | "reopen",
  note: string,
): Promise<MatchCase> {
  return sendJson<MatchCase>("POST", `/api/match-cases/${caseId}/decision`, {
    decision,
    note: note || null,
  });
}

/** Correct a value the AI misread. Throws the API's explanation if it's not valid. */
export async function correctField(
  documentId: number,
  field: string,
  value: string,
): Promise<DocumentDetail> {
  return sendJson<DocumentDetail>("PATCH", `/api/documents/${documentId}/fields`, {
    field,
    value,
  });
}

/** Everything that happened to a document and its 3-way match, newest first. */
export async function getHistory(documentId: number): Promise<AuditEvent[]> {
  return getJson<AuditEvent[]>(`/api/audit-events?document_id=${documentId}&limit=20`);
}

/** The 3-way match of an invoice, or null if it hasn't been checked yet. */
export async function getMatchCaseForInvoice(invoiceId: number): Promise<MatchCase | null> {
  const cases = await getJson<MatchCase[]>(`/api/match-cases?invoice_id=${invoiceId}`);
  return cases[0] ?? null;
}

/** Recently checked invoices first (up to 200, enough for the demo). */
export async function listMatchCases(): Promise<MatchCase[]> {
  return getJson<MatchCase[]>("/api/match-cases?limit=200");
}

/** Newest first. */
export async function listDocuments(): Promise<DocumentRow[]> {
  return getJson<DocumentRow[]>("/api/documents?limit=500");
}

/** The activity log, newest first. */
export async function listAuditEvents(): Promise<AuditEvent[]> {
  return getJson<AuditEvent[]>("/api/audit-events?limit=300");
}

export async function getDashboard(): Promise<Dashboard> {
  return getJson<Dashboard>("/api/dashboard");
}

export async function getBatch(id: number): Promise<BatchDetail> {
  return getJson<BatchDetail>(`/api/batches/${id}`);
}

export async function getDocument(id: number): Promise<DocumentDetail> {
  return getJson<DocumentDetail>(`/api/documents/${id}`);
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status}): ${url}`);
  }
  return (await response.json()) as T;
}

async function sendJson<T>(method: "POST" | "PATCH", url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    // FastAPI sends our messages as a string; validation errors as a list.
    const detail = typeof data.detail === "string" ? data.detail : "That didn't work. Check the value.";
    throw new Error(detail);
  }
  return data as T;
}
