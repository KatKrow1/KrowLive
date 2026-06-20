"use client";

import { Company } from "@/lib/api";
import { currencyForCountry } from "@/lib/constants";
import { cn } from "@/lib/utils";
import {
  Copy,
  ExternalLink,
  Facebook,
  Instagram,
  Linkedin,
  Twitter,
  X,
} from "lucide-react";

type CompanySheetProps = {
  company: Company | null;
  onClose: () => void;
};

function SocialIcon({ href, label, children }: { href: string; label: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      title={label}
      className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-muted/40 text-muted-foreground transition hover:border-violet-500/50 hover:text-violet-300"
    >
      {children}
    </a>
  );
}

export function CompanySheet({ company, onClose }: CompanySheetProps) {
  if (!company) return null;

  const social = company.social_links ?? {};
  const copyEmail = async (email: string) => {
    await navigator.clipboard.writeText(email);
  };

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col border-l border-border bg-card shadow-2xl">
        <div className="flex items-start justify-between border-b border-border p-6">
          <div>
            <h2 className="text-xl font-semibold">{company.name}</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {[company.city, company.state, company.country].filter(Boolean).join(", ")}
              {" · "}
              {currencyForCountry(company.country)}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto p-6">
          {company.summary && (
            <section>
              <h3 className="mb-2 text-sm font-medium uppercase tracking-wide text-muted-foreground">
                Summary
              </h3>
              <p className="text-sm leading-relaxed text-foreground/90">{company.summary}</p>
            </section>
          )}

          {company.tech_stack_signals && company.tech_stack_signals.length > 0 && (
            <section>
              <h3 className="mb-2 text-sm font-medium uppercase tracking-wide text-muted-foreground">
                Tech Stack Signals
              </h3>
              <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                {company.tech_stack_signals.map((signal) => (
                  <li key={signal}>{signal}</li>
                ))}
              </ul>
            </section>
          )}

          <section className="flex flex-wrap gap-3">
            <a
              href={company.website}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
            >
              <ExternalLink className="h-4 w-4" />
              Visit Website
            </a>
            {company.google_rating != null && (
              <span className="inline-flex items-center rounded-lg border border-border px-3 py-2 text-sm">
                Google {company.google_rating}★
              </span>
            )}
          </section>

          {(social.linkedin || social.twitter || social.instagram || social.facebook) && (
            <section>
              <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted-foreground">
                Social Links
              </h3>
              <div className="flex gap-2">
                {social.linkedin && (
                  <SocialIcon href={social.linkedin} label="LinkedIn">
                    <Linkedin className="h-4 w-4" />
                  </SocialIcon>
                )}
                {social.twitter && (
                  <SocialIcon href={social.twitter} label="Twitter/X">
                    <Twitter className="h-4 w-4" />
                  </SocialIcon>
                )}
                {social.instagram && (
                  <SocialIcon href={social.instagram} label="Instagram">
                    <Instagram className="h-4 w-4" />
                  </SocialIcon>
                )}
                {social.facebook && (
                  <SocialIcon href={social.facebook} label="Facebook">
                    <Facebook className="h-4 w-4" />
                  </SocialIcon>
                )}
              </div>
            </section>
          )}

          <section>
            <h3 className="mb-3 text-sm font-medium uppercase tracking-wide text-muted-foreground">
              Executives
            </h3>
            {!company.executives?.length ? (
              <p className="text-sm text-muted-foreground">No executives found on company website.</p>
            ) : (
              <div className="space-y-3">
                {company.executives.map((exec) => (
                  <div key={exec.id ?? exec.name} className="rounded-xl border border-border bg-muted/20 p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="font-medium">{exec.name}</p>
                        {exec.title && <p className="text-sm text-muted-foreground">{exec.title}</p>}
                      </div>
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-xs capitalize",
                          exec.consent_status === "opted_in"
                            ? "bg-emerald-500/15 text-emerald-300"
                            : exec.consent_status === "opted_out"
                              ? "bg-red-500/15 text-red-300"
                              : "bg-muted text-muted-foreground"
                        )}
                      >
                        {exec.consent_status.replace("_", " ")}
                      </span>
                    </div>
                    <div className="mt-3 space-y-1 text-sm text-muted-foreground">
                      {exec.email && (
                        <div className="flex items-center gap-2">
                          <span>{exec.email}</span>
                          <button
                            type="button"
                            onClick={() => copyEmail(exec.email!)}
                            className="inline-flex items-center gap-1 rounded border border-border px-2 py-0.5 text-xs hover:bg-muted"
                          >
                            <Copy className="h-3 w-3" /> Copy Email
                          </button>
                        </div>
                      )}
                      {exec.phone && <p>{exec.phone}</p>}
                      {exec.linkedin_url && (
                        <a
                          href={exec.linkedin_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-violet-300 hover:underline"
                        >
                          <Linkedin className="h-3.5 w-3.5" /> LinkedIn profile
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </aside>
    </>
  );
}
