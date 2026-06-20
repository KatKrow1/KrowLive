"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  ExternalLink,
  Facebook,
  Instagram,
  Linkedin,
  Mail,
  Phone,
  Twitter,
  X,
} from "lucide-react";
import { Company } from "@/lib/api";
import { currencyForCountry } from "@/lib/constants";
import { cn } from "@/lib/utils";

function initials(name: string) {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

type Props = {
  company: Company | null;
  onClose: () => void;
};

export function CompanySheet({ company, onClose }: Props) {
  if (!company) return null;

  const social = company.social_links ?? {};

  return (
    <AnimatePresence>
      <>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
          onClick={onClose}
        />
        <motion.aside
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ type: "spring", damping: 28, stiffness: 320 }}
          className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col border-l border-border/80 bg-card shadow-2xl"
        >
          <div className="flex items-start justify-between border-b border-border/60 p-6">
            <div>
              <h2 className="text-xl font-semibold">{company.name}</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {[company.city, company.state, company.country].filter(Boolean).join(", ")} ·{" "}
                {currencyForCountry(company.country)}
              </p>
            </div>
            <button type="button" onClick={onClose} className="rounded-lg p-2 hover:bg-muted">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex-1 space-y-6 overflow-y-auto p-6">
            {company.summary && (
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-primary">AI Summary</p>
                <p className="mt-2 text-sm leading-relaxed">{company.summary}</p>
              </div>
            )}

            {company.tech_stack_signals && company.tech_stack_signals.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Tech stack signals</p>
                <div className="flex flex-wrap gap-2">
                  {company.tech_stack_signals.map((s) => (
                    <span key={s} className="rounded-full border border-border bg-muted/40 px-2.5 py-1 text-xs">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <a
                href={company.website}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white"
              >
                <ExternalLink className="h-4 w-4" /> Visit Website
              </a>
              {(social.linkedin || social.twitter || social.instagram || social.facebook) && (
                <div className="flex gap-2">
                  {social.linkedin && (
                    <a href={social.linkedin} target="_blank" rel="noopener noreferrer" className="rounded-lg border border-border p-2 hover:border-primary/50">
                      <Linkedin className="h-4 w-4" />
                    </a>
                  )}
                  {social.twitter && (
                    <a href={social.twitter} target="_blank" rel="noopener noreferrer" className="rounded-lg border border-border p-2 hover:border-primary/50">
                      <Twitter className="h-4 w-4" />
                    </a>
                  )}
                  {social.instagram && (
                    <a href={social.instagram} target="_blank" rel="noopener noreferrer" className="rounded-lg border border-border p-2 hover:border-primary/50">
                      <Instagram className="h-4 w-4" />
                    </a>
                  )}
                  {social.facebook && (
                    <a href={social.facebook} target="_blank" rel="noopener noreferrer" className="rounded-lg border border-border p-2 hover:border-primary/50">
                      <Facebook className="h-4 w-4" />
                    </a>
                  )}
                </div>
              )}
            </div>

            <div>
              <p className="mb-3 text-xs font-medium uppercase text-muted-foreground">Executives</p>
              {!company.executives?.length ? (
                <p className="text-sm text-muted-foreground">None found on company website.</p>
              ) : (
                <div className="space-y-3">
                  {company.executives.map((exec) => (
                    <div key={exec.id ?? exec.name} className="rounded-xl border border-border/60 bg-muted/20 p-4">
                      <div className="flex gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary/30 to-accent/30 text-sm font-semibold">
                          {initials(exec.name)}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <p className="font-medium">{exec.name}</p>
                              {exec.title && <p className="text-sm text-muted-foreground">{exec.title}</p>}
                            </div>
                            <span
                              className={cn(
                                "shrink-0 rounded-full px-2 py-0.5 text-xs capitalize",
                                exec.consent_status === "opted_in"
                                  ? "bg-success/15 text-emerald-300"
                                  : exec.consent_status === "opted_out"
                                    ? "bg-red-500/15 text-red-300"
                                    : "bg-muted text-muted-foreground"
                              )}
                            >
                              {exec.consent_status.replace("_", " ")}
                            </span>
                          </div>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {exec.email && (
                              <button
                                type="button"
                                onClick={() => navigator.clipboard.writeText(exec.email!)}
                                className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs hover:bg-muted"
                              >
                                <Mail className="h-3 w-3" /> Copy Email
                              </button>
                            )}
                            {exec.phone && (
                              <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                                <Phone className="h-3 w-3" /> {exec.phone}
                              </span>
                            )}
                            {exec.linkedin_url && (
                              <a
                                href={exec.linkedin_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                              >
                                <Linkedin className="h-3 w-3" /> LinkedIn
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </motion.aside>
      </>
    </AnimatePresence>
  );
}
