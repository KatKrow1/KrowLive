"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { AlertCircle, ChevronRight, MapPin, Radar } from "lucide-react";
import { CompaniesBreadcrumb } from "@/components/companies/CompaniesBreadcrumb";
import { useStates } from "@/hooks/useHierarchy";
import {
  companiesStatePath,
  countryLabel,
  currencyForCountry,
  isCountryCode,
} from "@/lib/constants";
import { cn } from "@/lib/utils";

export default function CompaniesStatesPage() {
  const params = useParams();
  const countryParam = String(params.country ?? "");
  const country = isCountryCode(countryParam) ? countryParam : null;
  const { data: states = [], isLoading, isError, error } = useStates(country ?? "CA");

  if (!country) {
    return (
      <div className="glass rounded-xl p-12 text-center">
        <p className="font-medium">Invalid country</p>
        <Link href="/companies" className="mt-4 inline-block text-sm text-primary hover:underline">
          Back to countries
        </Link>
      </div>
    );
  }

  const label = countryLabel(country);

  return (
    <div className="space-y-6">
      <CompaniesBreadcrumb
        items={[{ label: "Countries", href: "/companies" }, { label: label }]}
      />

      <div>
        <h1 className="text-2xl font-semibold">{label}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {isLoading ? "Loading states…" : `${states.length} states · ${currencyForCountry(country)}`}
        </p>
      </div>

      {isError && (
        <div className="glass flex items-start gap-3 rounded-xl border border-destructive/40 p-4 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-medium">Failed to load states</p>
            <p className="mt-1 text-muted-foreground">
              {error instanceof Error ? error.message : "Check that the backend is running."}
            </p>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl bg-muted/50" />
          ))}
        </div>
      ) : states.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center shadow-soft">
          <MapPin className="mx-auto h-10 w-10 text-muted-foreground" />
          <p className="mt-4 font-medium">No states found</p>
          <p className="mt-2 text-sm text-muted-foreground">
            Companies may not be linked to states yet. Run discovery or the hierarchy migration.
          </p>
          <Link
            href="/discovery"
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white"
          >
            <Radar className="h-4 w-4" />
            Run Discovery
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {states.map((region, index) => (
            <motion.div
              key={region.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.03 }}
            >
              <Link
                href={companiesStatePath(country, region.slug)}
                className={cn(
                  "group flex h-full flex-col rounded-xl border border-border bg-card/60 p-5 shadow-soft transition",
                  "hover:border-primary/40 hover:bg-primary/5"
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <h2 className="font-semibold leading-snug">{region.name}</h2>
                  <ChevronRight className="h-5 w-5 shrink-0 text-muted-foreground transition group-hover:text-primary" />
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
