"use client";

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Download } from "lucide-react";
import { CompaniesBreadcrumb } from "@/components/companies/CompaniesBreadcrumb";
import { CompaniesTable } from "@/components/companies/CompaniesTable";
import { useCompanies, useStateId } from "@/hooks/useHierarchy";
import { useAppContext } from "@/lib/context";
import { api, CompanySummary, LeadStatus } from "@/lib/api";
import {
  companiesCountryPath,
  companyDetailPath,
  countryLabel,
  isCountryCode,
} from "@/lib/constants";

function filterCompanies(items: CompanySummary[], search: string) {
  const q = search.trim().toLowerCase();
  if (!q) return items;
  return items.filter((c) => c.name.toLowerCase().includes(q));
}

function sortCompanies(items: CompanySummary[], key: string, dir: "asc" | "desc") {
  const mult = dir === "asc" ? 1 : -1;
  return [...items].sort((a, b) => {
    const av = a[key as keyof CompanySummary];
    const bv = b[key as keyof CompanySummary];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    return String(av).localeCompare(String(bv)) * mult;
  });
}

export default function CompaniesStateListPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const params = useParams();
  const { search } = useAppContext();
  const countryParam = String(params.country ?? "");
  const stateSlug = String(params.state ?? "");
  const country = isCountryCode(countryParam) ? countryParam : null;

  const [sortKey, setSortKey] = useState("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkStatus, setBulkStatus] = useState<LeadStatus>("contacted");
  const [rescrapingId, setRescrapingId] = useState<string | null>(null);

  const { stateId, state, isLoading: stateLoading, isError: stateError } = useStateId(
    country ?? "CA",
    stateSlug
  );
  const {
    data: companies = [],
    isLoading: companiesLoading,
    isError: companiesError,
    error,
  } = useCompanies(stateId);

  const isLoading = stateLoading || companiesLoading;
  const isError = stateError || companiesError;
  const filtered = useMemo(() => filterCompanies(companies, search), [companies, search]);
  const sorted = useMemo(
    () => sortCompanies(filtered, sortKey, sortDir),
    [filtered, sortKey, sortDir]
  );

  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["companies", stateId] });
  }, [queryClient, stateId]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === sorted.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(sorted.map((c) => c.id)));
    }
  };

  const handleStatusChange = async (id: string, status: LeadStatus) => {
    await api.updateCompanyStatus(id, status);
    invalidate();
  };

  const handleBulkStatus = async () => {
    if (selectedIds.size === 0) return;
    await api.bulkUpdateStatus(Array.from(selectedIds), bulkStatus);
    setSelectedIds(new Set());
    invalidate();
  };

  const handleRescrape = async (id: string) => {
    setRescrapingId(id);
    try {
      await api.rescrapeCompany(id);
      invalidate();
    } finally {
      setRescrapingId(null);
    }
  };

  const handleExport = () => {
    api.exportCompaniesCsv({
      country: country ?? undefined,
      state_id: stateId ?? undefined,
    });
  };

  if (!country) {
    return (
      <div className="glass rounded-xl p-12 text-center">
        <p className="font-medium">Invalid country</p>
      </div>
    );
  }

  const countryName = countryLabel(country);
  const displayState =
    state?.name ??
    stateSlug
      .split("-")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");

  return (
    <div className="space-y-4">
      <CompaniesBreadcrumb
        items={[
          { label: "Countries", href: "/companies" },
          { label: countryName, href: companiesCountryPath(country) },
          { label: displayState },
        ]}
      />

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{displayState}</h1>
          <p className="text-sm text-muted-foreground">
            {isLoading ? "Loading…" : `${sorted.length} companies in ${countryName}`}
            {search ? ` · filtered by “${search}”` : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={handleExport}
          className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-muted"
        >
          <Download className="h-4 w-4" />
          Export CSV
        </button>
      </div>

      {selectedIds.size > 0 && (
        <div className="glass flex flex-wrap items-center gap-3 rounded-xl px-4 py-3 text-sm">
          <span>{selectedIds.size} selected</span>
          <select
            value={bulkStatus}
            onChange={(e) => setBulkStatus(e.target.value as LeadStatus)}
            className="rounded-md border border-border bg-background px-2 py-1"
          >
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="replied">Replied</option>
            <option value="not_interested">Not interested</option>
          </select>
          <button
            type="button"
            onClick={handleBulkStatus}
            className="rounded-lg bg-primary px-3 py-1.5 text-primary-foreground"
          >
            Apply status
          </button>
        </div>
      )}

      {isError && (
        <div className="glass flex items-start gap-3 rounded-xl border border-destructive/40 p-4 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-medium">Failed to load companies</p>
            <p className="mt-1 text-muted-foreground">
              {error instanceof Error ? error.message : "Check that the backend is running."}
            </p>
          </div>
        </div>
      )}

      {!isLoading && !isError && stateId == null && (
        <div className="glass rounded-xl p-12 text-center shadow-soft">
          <p className="font-medium">No states found</p>
          <p className="mt-2 text-sm text-muted-foreground">
            Could not resolve “{stateSlug}”. Go back and pick a state from the list.
          </p>
        </div>
      )}

      {(stateId != null || isLoading) && (
        <CompaniesTable
          companies={sorted}
          loading={isLoading}
          onSelect={(company) => router.push(companyDetailPath(company.id))}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={handleSort}
          emptyMessage="No companies found"
          selectedIds={selectedIds}
          onToggleSelect={toggleSelect}
          onToggleSelectAll={toggleSelectAll}
          onStatusChange={handleStatusChange}
          onRescrape={handleRescrape}
          rescrapingId={rescrapingId}
        />
      )}

      <Link
        href={companiesCountryPath(country)}
        className="inline-block text-sm text-muted-foreground hover:text-primary"
      >
        ← Back to states
      </Link>
    </div>
  );
}
