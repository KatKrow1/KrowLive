"use client";

import { useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { CompanySummary, LeadStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

function LetterAvatar({ name }: { name: string }) {
  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-xs font-semibold text-primary">
      {name.charAt(0).toUpperCase()}
    </div>
  );
}

const STATUS_STYLES: Record<LeadStatus, string> = {
  new: "bg-sky-500/15 text-sky-300",
  contacted: "bg-amber-500/15 text-amber-300",
  replied: "bg-emerald-500/15 text-emerald-300",
  not_interested: "bg-muted text-muted-foreground",
};

const STATUS_LABELS: Record<LeadStatus, string> = {
  new: "New",
  contacted: "Contacted",
  replied: "Replied",
  not_interested: "Not interested",
};

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return "Never";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 48) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

type Props = {
  companies: CompanySummary[];
  loading: boolean;
  onSelect: (c: CompanySummary) => void;
  sortKey?: string;
  sortDir?: "asc" | "desc";
  onSort?: (key: string) => void;
  emptyMessage?: string;
  selectedIds?: Set<string>;
  onToggleSelect?: (id: string) => void;
  onToggleSelectAll?: () => void;
  onStatusChange?: (id: string, status: LeadStatus) => void;
  onRescrape?: (id: string) => void;
  rescrapingId?: string | null;
};

export function CompaniesTable({
  companies,
  loading,
  onSelect,
  sortKey,
  sortDir,
  onSort,
  emptyMessage = "Run discovery to populate your pipeline.",
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onStatusChange,
  onRescrape,
  rescrapingId,
}: Props) {
  const [openStatusId, setOpenStatusId] = useState<string | null>(null);

  const th = (key: string, label: string) => (
    <th
      className={cn(
        "px-4 py-3 text-left text-xs uppercase tracking-wide text-muted-foreground",
        onSort && "cursor-pointer hover:text-foreground"
      )}
      onClick={onSort ? () => onSort(key) : undefined}
    >
      {label}
      {sortKey === key ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
    </th>
  );

  if (loading) {
    return (
      <div className="glass rounded-xl p-4 shadow-soft">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="mb-2 h-12 animate-pulse rounded-lg bg-muted/50" />
        ))}
      </div>
    );
  }

  if (companies.length === 0) {
    return (
      <div className="glass rounded-xl p-12 text-center shadow-soft">
        <p className="font-medium">No companies yet</p>
        <p className="mt-2 text-sm text-muted-foreground">{emptyMessage}</p>
      </div>
    );
  }

  const allSelected =
    selectedIds && companies.length > 0 && companies.every((c) => selectedIds.has(c.id));

  return (
    <div className="glass overflow-hidden rounded-xl shadow-soft">
      <div className="max-h-[calc(100vh-16rem)] overflow-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="sticky top-0 z-10 bg-card/95 backdrop-blur">
            <tr className="border-b border-border/80 text-left">
              {onToggleSelectAll && (
                <th className="w-10 px-3 py-3">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={onToggleSelectAll}
                    aria-label="Select all"
                  />
                </th>
              )}
              {th("name", "Company")}
              <th className="px-4 py-3 text-left text-xs uppercase tracking-wide text-muted-foreground">
                Status
              </th>
              <th className="px-4 py-3 text-left text-xs uppercase tracking-wide text-muted-foreground">
                Score
              </th>
              <th className="px-4 py-3 text-left text-xs uppercase tracking-wide text-muted-foreground">
                Last scraped
              </th>
              <th className="w-12 px-2 py-3" />
            </tr>
          </thead>
          <tbody>
            {companies.map((company) => {
              const status = (company.lead_status ?? "new") as LeadStatus;
              return (
                <tr
                  key={company.id}
                  className="border-b border-border/40 transition hover:bg-primary/5"
                >
                  {onToggleSelect && selectedIds && (
                    <td className="px-3 py-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(company.id)}
                        onChange={() => onToggleSelect(company.id)}
                        aria-label={`Select ${company.name}`}
                      />
                    </td>
                  )}
                  <td className="cursor-pointer px-4 py-3" onClick={() => onSelect(company)}>
                    <div className="flex items-center gap-3">
                      <LetterAvatar name={company.name} />
                      <span className="font-medium">{company.name}</span>
                    </div>
                  </td>
                  <td className="relative px-4 py-3" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className={cn(
                        "rounded-full px-2.5 py-0.5 text-xs font-medium",
                        STATUS_STYLES[status]
                      )}
                      onClick={() =>
                        setOpenStatusId(openStatusId === company.id ? null : company.id)
                      }
                    >
                      {STATUS_LABELS[status]}
                    </button>
                    {openStatusId === company.id && onStatusChange && (
                      <div className="absolute left-4 top-full z-20 mt-1 min-w-[140px] rounded-lg border border-border bg-card py-1 shadow-lg">
                        {(Object.keys(STATUS_LABELS) as LeadStatus[]).map((s) => (
                          <button
                            key={s}
                            type="button"
                            className="block w-full px-3 py-1.5 text-left text-xs hover:bg-muted"
                            onClick={() => {
                              onStatusChange(company.id, s);
                              setOpenStatusId(null);
                            }}
                          >
                            {STATUS_LABELS[s]}
                          </button>
                        ))}
                      </div>
                    )}
                  </td>
                  <td
                    className="cursor-pointer px-4 py-3 text-muted-foreground"
                    onClick={() => onSelect(company)}
                  >
                    {company.lead_score ?? "—"}
                  </td>
                  <td
                    className="cursor-pointer px-4 py-3 text-muted-foreground"
                    onClick={() => onSelect(company)}
                  >
                    {relativeTime(company.last_scraped_at)}
                  </td>
                  <td className="px-2 py-3" onClick={(e) => e.stopPropagation()}>
                    {onRescrape && (
                      <button
                        type="button"
                        title="Re-scrape website"
                        className="rounded-lg p-2 hover:bg-muted"
                        disabled={rescrapingId === company.id}
                        onClick={() => onRescrape(company.id)}
                      >
                        {rescrapingId === company.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCw className="h-4 w-4 text-muted-foreground" />
                        )}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
