import type { Metadata } from "next";

import { PageHeader } from "@/components/ledger/page-header";
import { UploadWorkspace } from "@/components/upload-workspace";

export const metadata: Metadata = { title: "Upload" };

export default function UploadPage() {
  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Upload documents"
        description="Add invoices, purchase orders and goods receipts as PDF or image files. The AI reads each one, then matches the invoice against its order and receipt."
      />
      <UploadWorkspace />
    </>
  );
}
