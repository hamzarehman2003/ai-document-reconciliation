import type { Metadata } from "next";
import Link from "next/link";
import { Upload } from "lucide-react";

import { PageHeader } from "@/components/ledger/page-header";
import { OverviewDashboard } from "@/components/overview/overview-dashboard";
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
      <OverviewDashboard />
    </>
  );
}
