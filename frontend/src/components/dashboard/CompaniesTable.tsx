"use client";

import { Company } from "@/lib/api";
import { cn } from "@/lib/utils";

function scoreColor(score: number | null | undefined) {
  if (score == null) return "text-muted-foreground bg-muted";
  if (score >= 70) return "text-emerald-300 bg-emerald-500/15";
  if (score >= 50) return "text-amber-300 bg-amber-500/15";
  return "text-muted-foreground bg-muted";
}

function ConsentBadge({ status }: { status: string }) {
  const styles =
    status === "opted_in"
      ? "bg-emerald-500/15 text-emerald-300"
      : status === "opted_out"
        ? "bg-red-500/15 text-red-300"
        : "bg-muted text-muted-foreground";
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-xs capitalize", styles)}>
      {status.replace("_", " ")}
    </span>
  );
}

type CompaniesTableProps = {
  companies: Company[];
  loading: boolean;
  onSelect: (company: Company) => void;
  sortKey: string;
  sortDir: "asc" | "desc";
  onSort: (key: string) => void;
};

export function CompaniesTable({
  companies,
  loading,
  onSelect,
  sortKey,
  sortDir,
  onSort,
}: CompaniesTableProps) {
  const th = (key: string, label: string) => (
    <th
      className="cursor-pointer px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground hover:text-foreground"
      onClick={() => onSort(key)}
    >
      {label}
      {sortKey === key ? (sortDir === "asc" ? " ↑" : " ↓") : ""}
    </th>
  );

  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-card p-6">
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-12 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      </div>
    );
  }

  if (companies.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-12 text-center">
        <p className="text-lg font-medium">No companies yet</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Run discovery or upload a CSV to populate your pipeline.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-sm">
          <thead className="border-b border-border bg-muted/30">
            <tr>
              {th("name", "Company")}
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Location
              </th>
              {th("lead_score", "Lead Score")}
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Source
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Top Executive
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Consent
              </th>
            </tr>
          </thead>
          <tbody>
            {companies.map((company) => {
              const topExec = company.executives?.[0];
              return (
                <tr
                  key={company.id ?? company.website}
                  onClick={() => onSelect(company)}
                  className="cursor-pointer border-b border-border/60 transition hover:bg-muted/20"
                >
                  <td className="px-4 py-3 font-medium">{company.name}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {[company.city, company.state].filter(Boolean).join(", ") || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "rounded-full px-2.5 py-1 text-xs font-medium",
                        scoreColor(company.lead_score)
                      )}
                    >
                      {company.lead_score ?? "—"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-violet-500/15 px-2 py-0.5 text-xs text-violet-300">
                      {company.source === "google_places" ? "Places" : "CSV"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {topExec ? `${topExec.name}${topExec.title ? ` · ${topExec.title}` : ""}` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <ConsentBadge status={topExec?.consent_status ?? "unknown"} />
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
