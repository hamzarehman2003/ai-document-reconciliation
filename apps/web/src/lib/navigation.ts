import {
  ClipboardCheck,
  FileSpreadsheet,
  Files,
  History,
  LayoutDashboard,
  Upload,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  title: string;
  href: string;
  icon: LucideIcon;
  description: string;
};

/** Every page in the sidebar and the ⌘K menu, in one place. */
export const NAVIGATION: { label: string; items: NavItem[] }[] = [
  {
    label: "Workspace",
    items: [
      {
        title: "Overview",
        href: "/",
        icon: LayoutDashboard,
        description: "Key numbers and what needs attention",
      },
      {
        title: "Upload",
        href: "/upload",
        icon: Upload,
        description: "Add invoices, purchase orders and receipts",
      },
      {
        title: "Review",
        href: "/review",
        icon: ClipboardCheck,
        description: "Invoices waiting for a decision",
      },
    ],
  },
  {
    label: "Records",
    items: [
      {
        title: "Documents",
        href: "/documents",
        icon: Files,
        description: "Everything uploaded, and what was read",
      },
      {
        title: "Exports",
        href: "/exports",
        icon: FileSpreadsheet,
        description: "Approved invoices for your accounting system",
      },
      {
        title: "Activity",
        href: "/activity",
        icon: History,
        description: "Who did what, and when",
      },
    ],
  },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function findPage(pathname: string): NavItem | undefined {
  return NAVIGATION.flatMap((group) => group.items).find((item) =>
    isActive(pathname, item.href),
  );
}
