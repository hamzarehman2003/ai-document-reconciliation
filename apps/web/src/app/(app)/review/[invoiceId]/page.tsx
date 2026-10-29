import { Suspense } from "react";
import type { Metadata } from "next";

import { InvoiceWorkspace } from "@/components/review/invoice-workspace";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Invoice" };

// The id is only known at request time, so it's read inside <Suspense>
// and the rest of the page can still be prerendered.
export default function InvoicePage({ params }: PageProps<"/review/[invoiceId]">) {
  return (
    <Suspense fallback={<Skeleton className="h-[32rem]" />}>
      <Invoice params={params} />
    </Suspense>
  );
}

async function Invoice({ params }: { params: Promise<{ invoiceId: string }> }) {
  const { invoiceId } = await params;
  return <InvoiceWorkspace invoiceId={Number(invoiceId)} />;
}
