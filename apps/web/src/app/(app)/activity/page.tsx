import type { Metadata } from "next";

import { ActivityTimeline } from "@/components/activity/activity-timeline";
import { PageHeader } from "@/components/ledger/page-header";

export const metadata: Metadata = { title: "Activity" };

export default function ActivityPage() {
  return (
    <>
      <PageHeader
        eyebrow="Records"
        title="Activity"
        description="Every upload, AI read, correction, decision and export, with who did it and when."
      />
      <ActivityTimeline />
    </>
  );
}
