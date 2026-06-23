"use client";

import { CompanySummary } from "@/lib/api";
import { cn } from "@/lib/utils";

function LetterAvatar({ name }: { name: string }) {
  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-xs font-semibold text-primary">
      {name.charAt(0).toUpperCase()}
    </div>
  );
}

type Props = {
  companies: CompanySummary[];
  loading: boolean;
  onSelect: (c: CompanySummary) => void;
  sortKey?: string;
  sortDir?: "asc" | "desc";
  onSort?: (key: string) => void;
  emptyMessage?: string;
};

export function CompaniesTable({
  companies,
  loading,
  onSelect,
  sortKey,
  sortDir,
  onSort,
  emptyMessage = "Run discovery to populate your pipeline.",
}: Props) {
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

  return (
    <div className="glass overflow-hidden rounded-xl shadow-soft">
      <div className="max-h-[calc(100vh-16rem)] overflow-auto">
        <table className="w-full min-w-[400px] text-sm">
          <thead className="sticky top-0 z-10 bg-card/95 backdrop-blur">
            <tr className="border-b border-border/80 text-left">
              {th("name", "Company")}
            </tr>
          </thead>
          <tbody>
            {companies.map((company) => (
              <tr
                key={company.id}
                onClick={() => onSelect(company)}
                className="cursor-pointer border-b border-border/40 transition hover:bg-primary/5"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <LetterAvatar name={company.name} />
                    <span className="font-medium">{company.name}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
