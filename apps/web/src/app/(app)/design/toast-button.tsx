"use client";

import { toast } from "sonner";

import { Button } from "@/components/ui/button";

export function ToastButton() {
  return (
    <Button
      variant="outline"
      onClick={() =>
        toast.success("Invoice INV-2026-0418 approved", {
          description: "It will be included in the next Excel export.",
        })
      }
    >
      Show a toast
    </Button>
  );
}
