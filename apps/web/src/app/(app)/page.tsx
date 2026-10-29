import type { Metadata } from "next";
import Link from "next/link";
import { LayoutDashboard, Upload } from "lucide-react";

import { EmptyState } from "@/components/ledger/empty-state";
import { PageHeader } from "@/components/ledger/page-header";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "Overview" };

export default function OverviewPage() {
  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Overview"
        description="How many invoices came in, how many matched on their own, and what is waiting for you."
        actions={
          <Button asChild>
            <Link href="/upload">
              <Upload /> Upload documents
            </Link>
          </Button>
        }
      />
      <EmptyState
        icon={LayoutDashboard}
        title="The dashboard arrives in the next step"
        description="Key numbers, match rates and the exception queue will live here."
        action={
          <Button variant="outline" asChild>
            <Link href="/upload">Go to upload</Link>
          </Button>
        }
      />
    </>
  );
}
