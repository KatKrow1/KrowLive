"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { api, Company } from "@/lib/api";
import { useAppContext } from "@/lib/context";
import { CompaniesTable } from "@/components/companies/CompaniesTable";
import { CompanySheet } from "@/components/companies/CompanySheet";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 15;

export default function CompaniesPage() {
  const { country, search } = useAppContext();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Company | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const handleSelect = async (company: Company) => {
    setSelected(company);
    if (!company.id) return;
    setDetailLoading(true);
    try {
      const full = await api.getCompany(company.id);
      setSelected(full);
    } catch {
      /* keep list row data if detail fetch fails */
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    setPage(1);
  }, [country, search]);

  useEffect(() => {
    setLoading(true);
    api
      .getCompanies({ country, search: search || undefined, page, page_size: PAGE_SIZE })
      .then((res) => {
        setCompanies(res.items);
        setTotal(res.total);
      })
      .finally(() => setLoading(false));
  }, [country, search, page]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Companies</h1>
        <p className="text-sm text-muted-foreground">{total} leads in pipeline</p>
      </div>

      <CompaniesTable companies={companies} loading={loading} onSelect={handleSelect} />

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className={cn(
                "inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm",
                page <= 1 && "opacity-40"
              )}
            >
              <ChevronLeft className="h-4 w-4" /> Prev
            </button>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className={cn(
                "inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm",
                page >= totalPages && "opacity-40"
              )}
            >
              Next <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      <CompanySheet company={selected} loading={detailLoading} onClose={() => setSelected(null)} />
    </div>
  );
}
