import { SystemStatus } from "@/components/system-status";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-8 bg-muted/40 p-6">
      <div className="text-center">
        <h1 className="text-3xl font-semibold tracking-tight">InvoiceIQ</h1>
        <p className="mt-2 text-muted-foreground">
          AI invoice processing and 3-way matching
        </p>
      </div>
      <SystemStatus />
    </main>
  );
}
