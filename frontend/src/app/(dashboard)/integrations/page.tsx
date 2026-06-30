"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, Loader2, Trash2 } from "lucide-react";
import { api } from "@/lib/api";

export default function IntegrationsPage() {
  const queryClient = useQueryClient();
  const [url, setUrl] = useState("");

  const { data: webhooks = [], isLoading } = useQuery({
    queryKey: ["webhooks"],
    queryFn: () => api.getWebhooks(),
  });

  const createMutation = useMutation({
    mutationFn: (webhookUrl: string) => api.createWebhook(webhookUrl),
    onSuccess: () => {
      setUrl("");
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteWebhook(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["webhooks"] }),
  });

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Link2 className="h-6 w-6 text-primary" />
          Integrations
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          When a new company is discovered, KrowLive POSTs its data as JSON to each active webhook.
        </p>
      </div>

      <form
        className="glass space-y-3 rounded-xl p-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (url.trim()) createMutation.mutate(url.trim());
        }}
      >
        <label className="text-sm font-medium">Webhook URL</label>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://your-server.com/webhook"
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={createMutation.isPending || !url.trim()}
          className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50"
        >
          {createMutation.isPending ? "Adding…" : "Add webhook"}
        </button>
      </form>

      {isLoading && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading…
        </div>
      )}

      <div className="space-y-2">
        {webhooks.map((w) => (
          <div
            key={w.id}
            className="glass flex items-center justify-between gap-4 rounded-xl px-4 py-3 text-sm"
          >
            <span className="truncate font-mono text-xs">{w.url}</span>
            <button
              type="button"
              onClick={() => deleteMutation.mutate(w.id)}
              className="shrink-0 rounded-lg border border-border p-2 hover:bg-muted"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
        {!isLoading && webhooks.length === 0 && (
          <p className="text-sm text-muted-foreground">No webhooks configured.</p>
        )}
      </div>
    </div>
  );
}
