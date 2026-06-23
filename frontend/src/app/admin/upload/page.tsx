"use client";

import { useState } from "react";
import { api, CsvUploadResult } from "@/lib/api";

/**
 * Admin-only CSV re-upload page — NOT linked from the main dashboard.
 * Re-uploading the same file upserts on `website` and refreshes scraped/enriched data.
 */
export default function AdminUploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string>("");
  const [result, setResult] = useState<CsvUploadResult | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!file) {
      setStatus("Select a CSV file first.");
      return;
    }
    setBusy(true);
    setStatus("Uploading…");
    setResult(null);
    try {
      await api.uploadCsv(file);
      const poll = setInterval(async () => {
        try {
          const job = await api.getStatus();
          setStatus(job.message ?? job.status);
          if (job.status !== "running") {
            clearInterval(poll);
            const last = await api.getLastCsvResult();
            setResult(last);
            setBusy(false);
            setStatus("Done.");
          }
        } catch (e) {
          clearInterval(poll);
          setStatus(e instanceof Error ? e.message : "Poll failed");
          setBusy(false);
        }
      }, 2000);
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Upload failed");
      setBusy(false);
    }
  };

  return (
    <main style={{ fontFamily: "sans-serif", padding: 24, maxWidth: 640 }}>
      <h1>KrowLive — Admin CSV Upload</h1>
      <p style={{ color: "#666" }}>
        Internal only. Re-upload your dataset to refresh scraped signals and enrichment (upserts on
        website — no duplicates).
      </p>
      <p>
        <a href="/">← Back to dashboard</a>
      </p>
      <hr />
      <div style={{ marginTop: 16 }}>
        <input
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </div>
      <button
        type="button"
        disabled={busy || !file}
        onClick={submit}
        style={{ marginTop: 16, padding: "8px 16px" }}
      >
        {busy ? "Processing…" : "Upload CSV"}
      </button>
      {status && (
        <pre style={{ marginTop: 16, whiteSpace: "pre-wrap", background: "#f4f4f4", padding: 12 }}>
          {status}
        </pre>
      )}
      {result && (
        <pre style={{ marginTop: 16, background: "#eef", padding: 12 }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </main>
  );
}
