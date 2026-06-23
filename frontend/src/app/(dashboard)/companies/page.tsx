"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { AlertCircle, ChevronRight } from "lucide-react";
import { CompaniesBreadcrumb } from "@/components/companies/CompaniesBreadcrumb";
import { useCountries } from "@/hooks/useHierarchy";
import { companiesCountryPath, countryLabel, currencyForCountry } from "@/lib/constants";
import { cn } from "@/lib/utils";

const FLAGS: Record<string, string> = { CA: "🇨🇦", AU: "🇦🇺" };

export default function CompaniesCountriesPage() {
  const { data: countries = [], isLoading, isError, error } = useCountries();

  return (
    <div className="space-y-6">
      <CompaniesBreadcrumb items={[{ label: "Countries" }]} />

      <div>
        <h1 className="text-2xl font-semibold">Companies</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Browse by country, state, then company.
        </p>
      </div>

      {isError && (
        <div className="glass flex items-start gap-3 rounded-xl border border-destructive/40 p-4 text-sm text-destructive">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-medium">Failed to load countries</p>
            <p className="mt-1 text-muted-foreground">
              {error instanceof Error ? error.message : "Check that the backend is running."}
            </p>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {(["CA", "AU"] as const).map((code) => (
            <div key={code} className="h-40 animate-pulse rounded-xl bg-muted/50" />
          ))}
        </div>
      ) : countries.length === 0 ? (
        <div className="glass rounded-xl p-12 text-center shadow-soft">
          <p className="font-medium">No countries found</p>
          <p className="mt-2 text-sm text-muted-foreground">
            Run the hierarchy migration in Supabase, then refresh this page.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {countries.map((country, index) => {
            const code = country.code;
            return (
              <motion.div
                key={country.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <Link
                  href={companiesCountryPath(code)}
                  className={cn(
                    "group flex flex-col rounded-xl border border-border bg-card/60 p-6 shadow-soft transition",
                    "hover:border-primary/40 hover:bg-primary/5"
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-4xl">{FLAGS[code]}</span>
                      <div>
                        <h2 className="text-xl font-semibold">{countryLabel(code)}</h2>
                        <p className="text-sm text-muted-foreground">{currencyForCountry(code)}</p>
                      </div>
                    </div>
                    <ChevronRight className="h-5 w-5 text-muted-foreground transition group-hover:text-primary" />
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
