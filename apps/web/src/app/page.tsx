import Link from "next/link";

import { UploadWorkspace } from "@/components/upload-workspace";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col bg-muted/40">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-10">
        <header className="flex items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight">InvoiceIQ</h1>
            <p className="mt-1 text-muted-foreground">
              Upload a document and see what the AI reads from it.
            </p>
          </div>
          <Link href="/status" className="text-sm text-muted-foreground hover:text-foreground">
            System status
          </Link>
        </header>
        <UploadWorkspace />
      </div>
    </main>
  );
}
