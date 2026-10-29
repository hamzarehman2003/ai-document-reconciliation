import { StatTile } from "@/components/ledger/stat-tile";
import type { AmountByCurrency } from "@/lib/api";
import { formatMoney } from "@/lib/format";

type Props = {
  label: string;
  amounts: AmountByCurrency[];
  tone?: "default" | "success" | "danger";
  /** Shown when there is no amount at all. */
  emptyDetail: string;
};

/** Money is never added across currencies: the largest one big, the others underneath. */
export function MoneyTile({ label, amounts, tone = "default", emptyDetail }: Props) {
  const [first, ...others] = [...amounts].sort((a, b) => b.invoices - a.invoices);
  if (!first) {
    return <StatTile label={label} value={formatMoney("0", null)} detail={emptyDetail} />;
  }
  const invoices = amounts.reduce((sum, item) => sum + item.invoices, 0);
  return (
    <StatTile
      label={label}
      value={formatMoney(first.amount, first.currency)}
      tone={tone}
      detail={
        others.length > 0
          ? `and ${others.map((item) => formatMoney(item.amount, item.currency)).join(", ")} · ${invoices} invoices`
          : `${invoices} invoice${invoices === 1 ? "" : "s"}`
      }
    />
  );
}
