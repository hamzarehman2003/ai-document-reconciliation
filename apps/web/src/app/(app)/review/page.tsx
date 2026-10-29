import type { Metadata } from "next";

import { PageHeader } from "@/components/ledger/page-header";
import { ReviewQueue } from "@/components/review/review-queue";

export const metadata: Metadata = { title: "Review" };

export default function ReviewPage() {
  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Review"
        description="Every invoice checked against its purchase order and goods receipt. Open one to see what differs and approve or reject it."
      />
      <ReviewQueue />
    </>
  );
}
