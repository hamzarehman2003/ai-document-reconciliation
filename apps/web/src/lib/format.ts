import type { DocumentType } from "@/lib/api";

export const DOC_TYPE_LABELS: Record<DocumentType, string> = {
  invoice: "Invoice",
  purchase_order: "Purchase order",
  goods_receipt: "Goods receipt",
  unknown: "Unknown type",
};

/** Plain names for the 3-way match rule codes. */
export const PROBLEM_LABELS: Record<string, string> = {
  QTY_EXCEEDS_RECEIVED: "Billed more than received",
  PRICE_MISMATCH: "Price differs from the order",
  ITEM_NOT_ON_PO: "Item not on the order",
  LINE_TOTAL_MISMATCH: "Line total doesn't add up",
  TOTAL_MISMATCH: "Invoice total doesn't add up",
  MISSING_PO_REFERENCE: "No purchase order number",
  VENDOR_MISMATCH: "Vendor differs from the order",
  DUPLICATE_INVOICE: "Possible duplicate",
};

const EMPTY = "—";

/** "1234.5" + "EUR" → "€1,234.50". Display only; the exact value stays a string. */
export function formatMoney(value: string | null, currency: string | null): string {
  if (value === null) return EMPTY;
  const amount = Number(value);
  if (!currency) {
    return amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency}`; // unknown currency code
  }
}

/** "16.250" → "16.25" */
export function formatQuantity(value: string | null): string {
  return value === null ? EMPTY : String(Number(value));
}

/** "2026-01-23" → "23 Jan 2026" */
export function formatDate(value: string | null): string {
  if (!value) return EMPTY;
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** A timestamp as "just now", "3 hours ago", "2 days ago". */
export function formatAge(value: string): string {
  const minutes = Math.round((Date.now() - new Date(value).getTime()) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.round(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export function orDash(value: string | null): string {
  return value ?? EMPTY;
}
