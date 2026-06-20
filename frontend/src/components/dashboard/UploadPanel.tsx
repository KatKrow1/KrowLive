"use client";

import { useCallback, useState } from "react";
import { CheckCircle2, Loader2, Upload } from "lucide-react";
import { api, CsvUploadResult } from "@/lib/api";
import { cn } from "@/lib/utils";

type UploadPanelProps = {
  onComplete: () => void;
  jobRunning: boolean;
};

export function UploadPanel({ onComplete, jobRunning }: UploadPanelProps) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<CsvUploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.endsWith(".csv")) {
        setError("Please upload a CSV file");
        return;
      }
      setError(null);
      setUploading(true);
      setResult(null);
      try {
        await api.uploadCsv(file);
        const poll = setInterval(async () => {
          const status = await api.getStatus();
          if (status.status !== "running") {
            clearInterval(poll);
            const last = await api.getLastCsvResult();
            setResult(last);
            setUploading(false);
            onComplete();
          }
        }, 2000);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Upload failed");
        setUploading(false);
      }
    },
    [onComplete]
  );

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4 flex items-center gap-2">
        <Upload className="h-5 w-5 text-fuchsia-400" />
        <h2 className="text-lg font-semibold">Upload CSV</h2>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files[0];
          if (file) handleFile(file);
        }}
        className={cn(
          "flex min-h-[140px] cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed p-6 text-center transition",
          dragging ? "border-violet-500 bg-violet-500/10" : "border-border bg-muted/20"
        )}
      >
        <input
          type="file"
          accept=".csv"
          className="hidden"
          id="csv-upload"
          disabled={uploading || jobRunning}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        <label htmlFor="csv-upload" className="cursor-pointer">
          {uploading ? (
            <div className="flex flex-col items-center gap-2 text-muted-foreground">
              <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
              <p className="text-sm">Processing CSV…</p>
            </div>
          ) : (
            <>
              <Upload className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                Drag &amp; drop a CSV here, or click to browse
              </p>
            </>
          )}
        </label>
      </div>

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

      {result && (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
          <div>
            <p className="font-medium text-emerald-300">Upload complete</p>
            <p className="text-muted-foreground">
              {result.rows_new} new, {result.rows_updated} updated, {result.errors.length} errors
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
