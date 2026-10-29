import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

type Props = {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
};

/** Shown when there's nothing yet: a fine line icon, one serif line, one clear action. */
export function EmptyState({ icon: Icon, title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed px-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-full border bg-card shadow-paper">
        <Icon className="size-5 text-muted-foreground" strokeWidth={1.5} />
      </div>
      <p className="mt-5 font-heading text-xl font-medium tracking-[-0.01em]">{title}</p>
      <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-muted-foreground">
        {description}
      </p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
