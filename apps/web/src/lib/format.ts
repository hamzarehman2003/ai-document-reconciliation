import type { DocumentType } from "@/lib/api";

export const DOC_TYPE_LABELS: Record<DocumentType, string> = {
  invoice: "Invoice",
  purchase_order: "Purchase order",
  goods_receipt: "Goods receipt",
  unknown: "Unknown type",
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

export function orDash(value: string | null): string {
  return value ?? EMPTY;
}
