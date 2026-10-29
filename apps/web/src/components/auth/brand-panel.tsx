import { Fragment } from "react";
import { CircleCheck } from "lucide-react";

import { Logo } from "@/components/ledger/logo";

const DOCUMENTS = ["Invoice", "Purchase order", "Goods receipt"];

/** The left 60% of the login and sign-up pages: what the product does, in one glance. */
export function BrandPanel() {
  return (
    <aside className="relative hidden h-svh flex-col overflow-hidden bg-brand-panel p-12 text-brand-panel-foreground lg:sticky lg:top-0 lg:flex xl:p-16">
      {/* Faint ledger ruling, like accounting paper. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.05] [background-image:repeating-linear-gradient(to_bottom,currentColor_0,currentColor_1px,transparent_1px,transparent_44px)]"
      />

      <Logo tone="inverse" className="relative" />

      <div className="relative flex flex-1 flex-col justify-center">
        <p className="text-[0.6875rem] font-medium tracking-[0.14em] text-brand-panel-foreground/60 uppercase">
          Accounts payable, automated
        </p>
        <h1 className="mt-4 max-w-lg font-heading text-[2.25rem] leading-[1.1] font-medium tracking-[-0.025em] xl:text-[2.75rem]">
          Every invoice, checked against its order and its delivery.
        </h1>
        <p className="mt-4 max-w-md text-[0.9375rem] leading-relaxed text-brand-panel-foreground/70">
          AI reads the documents. Clear rules find what doesn&apos;t match.
        </p>

        <div className="mt-10 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm text-brand-panel-foreground/85">
          {DOCUMENTS.map((label, index) => (
            <Fragment key={label}>
              {index > 0 && <span className="text-brand-panel-foreground/35">↔</span>}
              <span className="flex items-center gap-1.5">
                <CircleCheck className="size-4 text-brand-panel-foreground/60" strokeWidth={1.75} />
                {label}
              </span>
            </Fragment>
          ))}
        </div>
      </div>
    </aside>
  );
}
