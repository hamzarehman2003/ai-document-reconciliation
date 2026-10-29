"use client";

import { useState, type KeyboardEvent } from "react";
import { Check, Pencil, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { correctField, type Correction, type DocumentDetail } from "@/lib/api";
import { cn } from "@/lib/utils";

type Props = {
  documentId: number;
  field: string; // "total", "line_items.2.quantity", ...
  display: string; // the formatted value shown
  raw: string | null; // the value to start editing from
  correction?: Correction;
  onSaved: (document: DocumentDetail) => void;
  className?: string;
};

/** A value with a pencil to correct it, and a "corrected" mark once it was fixed. */
export function EditableValue({
  documentId,
  field,
  display,
  raw,
  correction,
  onSaved,
  className,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEditing() {
    setDraft(raw ?? "");
    setError(null);
    setEditing(true);
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      onSaved(await correctField(documentId, field, draft));
      setEditing(false);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save.");
    } finally {
      setSaving(false);
    }
  }

  function handleKey(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") save();
    if (event.key === "Escape") setEditing(false);
  }

  if (editing) {
    return (
      // Clicks here must not also select the field or table row underneath.
      <span className="flex flex-col gap-1" onClick={(event) => event.stopPropagation()}>
        <span className="flex items-center gap-1">
          <Input
            autoFocus
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKey}
            className="h-7 min-w-24 font-mono text-sm"
            aria-label={`New value for ${field}`}
          />
          <Button size="icon-sm" onClick={save} disabled={saving} aria-label="Save">
            <Check />
          </Button>
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={() => setEditing(false)}
            aria-label="Cancel"
          >
            <X />
          </Button>
        </span>
        {error && <span className="text-xs text-destructive">{error}</span>}
      </span>
    );
  }

  return (
    <span className={cn("group inline-flex items-center gap-1", className)}>
      <span className="font-mono">{display}</span>
      {correction && (
        <span
          title={`Corrected by ${correction.corrected_by}. The AI read: ${correction.old_value ?? "nothing"}`}
          className="rounded bg-sky-500/10 px-1 text-[10px] font-medium text-sky-700 dark:text-sky-400"
        >
          corrected
        </span>
      )}
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          startEditing();
        }}
        aria-label="Correct this value"
        className="text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100 hover:text-foreground focus:opacity-100"
      >
        <Pencil className="size-3" />
      </button>
    </span>
  );
}
