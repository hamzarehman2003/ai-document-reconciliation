import Link from "next/link";

import { SystemStatus } from "@/components/system-status";

export default function StatusPage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 bg-muted/40 p-6">
      <SystemStatus />
      <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
        ← Back to upload
      </Link>
    </main>
  );
}
