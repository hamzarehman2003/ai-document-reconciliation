import { Suspense } from "react";
import type { Metadata } from "next";

import { ActivityTimeline } from "@/components/activity/activity-timeline";
import { PageHeader } from "@/components/ledger/page-header";
import { Skeleton } from "@/components/ui/skeleton";

export const metadata: Metadata = { title: "Activity" };

export default function ActivityPage() {
  return (
    <>
      <PageHeader
        eyebrow="Records"
        title="Activity"
        description="Every upload, AI read, correction, decision and export, with who did it and when."
      />
      {/* The timeline reads ?mine=1 from the URL, so it sits inside <Suspense>. */}
      <Suspense fallback={<Skeleton className="h-96" />}>
        <ActivityTimeline />
      </Suspense>
    </>
  );
}
