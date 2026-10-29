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
