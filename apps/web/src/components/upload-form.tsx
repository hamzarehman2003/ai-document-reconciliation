"use client";

import { useRef, useState, type DragEvent } from "react";
import { FileUp, Loader2, Upload } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { uploadFiles, type UploadResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

export function UploadForm({ onUploaded }: { onUploaded: (response: UploadResponse) => void }) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    setFiles(Array.from(event.dataTransfer.files));
  }

  async function handleUpload() {
    setUploading(true);
    setError(null);
    try {
      onUploaded(await uploadFiles(files));
      setFiles([]);
      if (inputRef.current) inputRef.current.value = "";
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload documents</CardTitle>
        <CardDescription>
          Invoices, purchase orders or goods receipts. PDF, PNG or JPEG, up to 20 files.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <label
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
            dragging ? "border-primary bg-primary/5" : "hover:bg-muted/50",
          )}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg"
            className="sr-only"
            onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
          />
          <FileUp className="size-8 text-muted-foreground" />
          <p className="text-sm font-medium">Drop files here, or click to choose</p>
          {files.length > 0 && (
            <p className="max-w-full truncate text-xs text-muted-foreground">
              {files.length} selected: {files.map((file) => file.name).join(", ")}
            </p>
          )}
        </label>
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </CardContent>
      <CardFooter>
        <Button onClick={handleUpload} disabled={files.length === 0 || uploading}>
          {uploading ? <Loader2 className="animate-spin" /> : <Upload />}
          {uploading ? "Uploading…" : `Upload ${files.length || ""} file${files.length === 1 ? "" : "s"}`}
        </Button>
      </CardFooter>
    </Card>
  );
}
