import type { ReactNode } from "react";

type Props = {
  eyebrow: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
};

/** The top of every page: small-caps eyebrow, serif title, one line of context. */
export function PageHeader({ eyebrow, title, description, actions }: Props) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4 border-b pb-6">
      <div className="min-w-0">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="mt-2 font-heading text-[2rem] leading-tight font-medium tracking-[-0.02em]">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  );
}
