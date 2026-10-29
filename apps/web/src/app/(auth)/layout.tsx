import { BrandPanel } from "@/components/auth/brand-panel";
import { Logo } from "@/components/ledger/logo";

/** Login and sign up: the product on the left (60%), the form on the right (40%).
 * On small screens only the form is shown. */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-svh lg:grid-cols-[3fr_2fr]">
      <BrandPanel />
      <main className="flex min-h-svh flex-col px-6 py-8 sm:px-12">
        <Logo className="lg:hidden" />
        <div className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-sm duration-300 animate-in fade-in slide-in-from-bottom-1">
            {children}
          </div>
        </div>
        <p className="text-center text-xs text-muted-foreground">
          A portfolio demo. Companies and documents are fictional.
        </p>
      </main>
    </div>
  );
}
