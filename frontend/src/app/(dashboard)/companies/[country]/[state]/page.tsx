"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { AlertCircle } from "lucide-react";
import { CompaniesBreadcrumb } from "@/components/companies/CompaniesBreadcrumb";
import { CompaniesTable } from "@/components/companies/CompaniesTable";
import { useCompanies, useStateId } from "@/hooks/useHierarchy";
import { useAppContext } from "@/lib/context";
import {
  companiesCountryPath,
  companyDetailPath,
  countryLabel,
  isCountryCode,
} from "@/lib/constants";
import { CompanySummary } from "@/lib/api";

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
  const params = useParams();
  const { search } = useAppContext();
  const countryParam = String(params.country ?? "");
  const stateSlug = String(params.state ?? "");
  const country = isCountryCode(countryParam) ? countryParam : null;

  const [sortKey, setSortKey] = useState("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

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

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
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

      <div>
        <h1 className="text-2xl font-semibold">{displayState}</h1>
        <p className="text-sm text-muted-foreground">
          {isLoading ? "Loading…" : `${sorted.length} companies in ${countryName}`}
          {search ? ` · filtered by “${search}”` : ""}
        </p>
      </div>

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
