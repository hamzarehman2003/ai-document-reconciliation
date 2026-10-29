"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";

import { CommandMenu } from "@/components/shell/command-menu";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { NAVIGATION, findPage } from "@/lib/navigation";

/** The thin bar above every page: sidebar toggle, where you are, search. */
export function SiteHeader() {
  return (
    <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-3 border-b bg-background/85 px-4 backdrop-blur-sm md:px-6">
      <SidebarTrigger className="-ml-1.5" />
      <Separator orientation="vertical" className="h-4!" />
      {/* The path can be unknown until request time (pages with an id in the URL). */}
      <Suspense fallback={<Breadcrumb pathname={null} />}>
        <CurrentBreadcrumb />
      </Suspense>
      <div className="ml-auto">
        <CommandMenu />
      </div>
    </header>
  );
}

function CurrentBreadcrumb() {
  return <Breadcrumb pathname={usePathname()} />;
}

function Breadcrumb({ pathname }: { pathname: string | null }) {
  const page = pathname === null ? undefined : findPage(pathname);
  const group = NAVIGATION.find((g) => g.items.some((item) => item === page));

  return (
    <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-2 text-sm">
      <span className="text-muted-foreground">{group?.label ?? "InvoiceIQ"}</span>
      {pathname !== null && (
        <>
          <span className="text-muted-foreground/50">/</span>
          <span className="truncate font-medium">{page?.title ?? "Design system"}</span>
        </>
      )}
    </nav>
  );
}
