"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bookmark, Loader2, Play, Trash2 } from "lucide-react";
import { api, SavedSearch } from "@/lib/api";

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "Never run";
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days < 1) return "Today";
  return `${days}d ago`;
}

export default function SavedSearchesPage() {
  const queryClient = useQueryClient();
  const [runningId, setRunningId] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<string | null>(null);

  const { data: searches = [], isLoading } = useQuery({
    queryKey: ["saved-searches"],
    queryFn: () => api.getSavedSearches(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteSavedSearch(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-searches"] }),
  });

  const handleRun = async (search: SavedSearch) => {
    setRunningId(search.id);
    setRunResult(null);
    try {
      const result = await api.runSavedSearch(search.id);
      setRunResult(`${result.new_count} new companies found (${result.total_processed} processed)`);
      queryClient.invalidateQueries({ queryKey: ["saved-searches"] });
    } catch (e) {
      setRunResult(e instanceof Error ? e.message : "Run failed");
    } finally {
      setRunningId(null);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Bookmark className="h-6 w-6 text-primary" />
          Saved Searches
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Re-run discovery and see only companies new since the last run.
        </p>
      </div>

      {runResult && (
        <div className="glass rounded-xl border border-primary/30 px-4 py-3 text-sm">{runResult}</div>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      )}

      {!isLoading && searches.length === 0 && (
        <div className="glass rounded-xl p-12 text-center">
          <p className="font-medium">No saved searches yet</p>
          <p className="mt-2 text-sm text-muted-foreground">
            Save a search from the Discovery flow to track new results over time.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {searches.map((s) => (
          <div key={s.id} className="glass flex flex-wrap items-center justify-between gap-4 rounded-xl p-4">
            <div>
              <p className="font-medium">{s.name}</p>
              <p className="text-sm text-muted-foreground">
                {s.industry} · {s.country} · {(s.cities || []).join(", ") || "All cities"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Last run: {relativeTime(s.last_run_at)}
                {s.last_result_count > 0 && (
                  <span className="ml-2 rounded-full bg-primary/15 px-2 py-0.5 text-primary">
                    {s.last_result_count} new last run
                  </span>
                )}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={runningId === s.id}
                onClick={() => handleRun(s)}
                className="inline-flex items-center gap-1 rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground"
              >
                {runningId === s.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                Run
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(s.id)}
                className="rounded-lg border border-border p-2 hover:bg-muted"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
