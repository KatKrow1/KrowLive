"use client";

import Image from "next/image";
import { Company } from "@/lib/api";
import { cn } from "@/lib/utils";

function faviconUrl(website: string) {
  try {
    const host = new URL(website.startsWith("http") ? website : `https://${website}`).hostname;
    return `https://www.google.com/s2/favicons?domain=${host}&sz=32`;
  } catch {
    return null;
  }
}

function LetterAvatar({ name }: { name: string }) {
  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-xs font-semibold text-primary">
      {name.charAt(0).toUpperCase()}
    </div>
  );
}

function ScoreBadge({ score }: { score: number | null | undefined }) {
  const cls =
    score == null
      ? "bg-muted text-muted-foreground"
      : score >= 70
        ? "bg-success/15 text-emerald-300"
        : score >= 50
          ? "bg-warning/15 text-amber-300"
          : "bg-muted text-muted-foreground";
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold", cls)}>
      {score ?? "—"}
    </span>
  );
}

type Props = {
  companies: Company[];
  loading: boolean;
  onSelect: (c: Company) => void;
};

export function CompaniesTable({ companies, loading, onSelect }: Props) {
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
        <p className="mt-2 text-sm text-muted-foreground">Run discovery to populate your pipeline.</p>
      </div>
    );
  }

  return (
    <div className="glass overflow-hidden rounded-xl shadow-soft">
      <div className="max-h-[calc(100vh-16rem)] overflow-auto">
        <table className="w-full min-w-[800px] text-sm">
          <thead className="sticky top-0 z-10 bg-card/95 backdrop-blur">
            <tr className="border-b border-border/80 text-left text-xs uppercase tracking-wide text-muted-foreground">
              <th className="px-4 py-3">Company</th>
              <th className="px-4 py-3">Industry</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Top Executive</th>
              <th className="px-4 py-3">Consent</th>
            </tr>
          </thead>
          <tbody>
            {companies.map((company) => {
              const favicon = faviconUrl(company.website);
              const top = company.executives?.[0];
              return (
                <tr
                  key={company.id ?? company.website}
                  onClick={() => onSelect(company)}
                  className="cursor-pointer border-b border-border/40 transition hover:bg-primary/5"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {favicon ? (
                        <Image src={favicon} alt="" width={32} height={32} className="rounded-lg" unoptimized />
                      ) : (
                        <LetterAvatar name={company.name} />
                      )}
                      <span className="font-medium">{company.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{company.category ?? "—"}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {[company.city, company.state].filter(Boolean).join(", ") || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <ScoreBadge score={company.lead_score} />
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
                      {company.source === "google_places" ? "Places" : "CSV"}
                    </span>
                  </td>
                  <td className="max-w-[180px] truncate px-4 py-3 text-muted-foreground">
                    {top ? `${top.name}${top.title ? ` · ${top.title}` : ""}` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs capitalize text-muted-foreground">
                      {(top?.consent_status ?? "unknown").replace("_", " ")}
                    </span>
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
