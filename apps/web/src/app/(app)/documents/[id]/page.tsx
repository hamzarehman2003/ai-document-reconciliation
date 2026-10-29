import { Suspense } from "react";
import type { Metadata } from "next";

import { DocumentWorkspace } from "@/components/document-workspace";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Document" };

// Same pattern as the invoice page: the id is read inside <Suspense>.
export default function DocumentPage({ params }: PageProps<"/documents/[id]">) {
  return (
    <Suspense fallback={<Skeleton className="h-[32rem]" />}>
      <DocumentById params={params} />
    </Suspense>
  );
}

async function DocumentById({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DocumentWorkspace documentId={Number(id)} backHref="/documents" backLabel="Documents" />;
}
