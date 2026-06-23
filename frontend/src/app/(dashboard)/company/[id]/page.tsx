"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { CompanySheet } from "@/components/companies/CompanySheet";
import { CompaniesBreadcrumb } from "@/components/companies/CompaniesBreadcrumb";
import { useCompany } from "@/hooks/useHierarchy";
import {
  companiesCountryPath,
  companiesStatePath,
  countryLabel,
  isCountryCode,
} from "@/lib/constants";

export default function CompanyDetailPage() {
  const params = useParams();
  const id = String(params.id ?? "");
  const { data: company, isLoading, isError } = useCompany(id);

  if (isLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center gap-2 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
        Loading company…
      </div>
    );
  }

  if (isError || !company) {
    return (
      <div className="glass rounded-xl p-12 text-center">
        <p className="font-medium">Company not found</p>
        <Link href="/companies" className="mt-4 inline-block text-sm text-primary hover:underline">
          Back to countries
        </Link>
      </div>
    );
  }

  const country = isCountryCode(company.country) ? company.country : "CA";
  const breadcrumbItems: { label: string; href?: string }[] = [
    { label: "Countries", href: "/companies" },
    { label: countryLabel(country), href: companiesCountryPath(country) },
  ];
  if (company.state_slug) {
    breadcrumbItems.push({
      label: company.state ?? company.state_slug,
      href: companiesStatePath(country, company.state_slug),
    });
  }
  breadcrumbItems.push({ label: company.name });

  return (
    <div className="space-y-4">
      <CompaniesBreadcrumb items={breadcrumbItems} />

      <Link
        href={
          company.state_slug
            ? companiesStatePath(country, company.state_slug)
            : companiesCountryPath(country)
        }
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-primary"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to list
      </Link>

      <div className="glass rounded-xl p-6 shadow-soft">
        <CompanySheet company={company} loading={false} onClose={() => {}} embedded />
      </div>
    </div>
  );
}
