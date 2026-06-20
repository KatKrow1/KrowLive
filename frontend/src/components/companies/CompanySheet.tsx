"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  ExternalLink,
  Facebook,
  Instagram,
  Linkedin,
  Loader2,
  Mail,
  MapPin,
  Phone,
  Star,
  Twitter,
  X,
} from "lucide-react";
import { Company, Executive } from "@/lib/api";
import { cn } from "@/lib/utils";

const JUNK_EXECUTIVE_NAMES = new Set([
  "linkedin",
  "follow",
  "twitter",
  "facebook",
  "instagram",
  "youtube",
  "contact",
  "email",
  "phone",
]);

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function isLikelyPerson(exec: NonNullable<Company["executives"]>[number]) {
  const name = exec.name.trim().toLowerCase();
  if (!name || JUNK_EXECUTIVE_NAMES.has(name)) return false;
  if (exec.extraction_confidence === "low" && !exec.title) return false;
  return true;
}

function confidenceBadge(confidence?: Executive["extraction_confidence"]) {
  if (!confidence) return null;
  const styles = {
    high: "bg-success/15 text-emerald-300",
    medium: "bg-primary/15 text-primary",
    low: "bg-muted text-muted-foreground",
  } as const;
  return (
    <span className={cn("shrink-0 rounded-full px-2 py-0.5 text-xs capitalize", styles[confidence])}>
      {confidence} confidence
    </span>
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
    <span className={cn("inline-flex rounded-full px-2.5 py-0.5 text-sm font-semibold", cls)}>
      {score ?? "—"}
    </span>
  );
}

type Props = {
  company: Company | null;
  loading?: boolean;
  onClose: () => void;
};

export function CompanySheet({ company, loading, onClose }: Props) {
  if (!company) return null;

  const social = company.social_links ?? {};
  const executives = (company.executives ?? []).filter(isLikelyPerson);
  const hasSocial = Boolean(social.linkedin || social.twitter || social.instagram || social.facebook);

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
            <div className="min-w-0 pr-4">
              <h2 className="text-xl font-semibold leading-tight">{company.name}</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {[company.city, company.state, company.country].filter(Boolean).join(", ")}
              </p>
            </div>
            <button type="button" onClick={onClose} className="shrink-0 rounded-lg p-2 hover:bg-muted">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="flex-1 space-y-6 overflow-y-auto p-6">
            {loading && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Loading full company details…
              </div>
            )}

            <section className="space-y-3 rounded-xl border border-border/60 bg-muted/10 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Company details</p>
              <dl className="grid gap-2 text-sm">
                {company.address && (
                  <div className="flex gap-2">
                    <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    <dd>{company.address}</dd>
                  </div>
                )}
                {company.phone && (
                  <div className="flex gap-2">
                    <Phone className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    <dd>
                      <a href={`tel:${company.phone}`} className="hover:text-primary hover:underline">
                        {company.phone}
                      </a>
                    </dd>
                  </div>
                )}
                <div className="flex gap-2">
                  <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  <dd>
                    <a
                      href={company.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="break-all text-primary hover:underline"
                    >
                      {company.website}
                    </a>
                  </dd>
                </div>
                {company.category && (
                  <div className="flex justify-between border-t border-border/40 pt-2">
                    <dt className="text-muted-foreground">Industry</dt>
                    <dd>{company.category}</dd>
                  </div>
                )}
                {(company.google_rating != null || company.google_review_count != null) && (
                  <div className="flex justify-between border-t border-border/40 pt-2">
                    <dt className="text-muted-foreground">Google rating</dt>
                    <dd className="inline-flex items-center gap-1">
                      {company.google_rating != null && (
                        <>
                          <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                          {company.google_rating}
                        </>
                      )}
                      {company.google_review_count != null && (
                        <span className="text-muted-foreground">
                          ({company.google_review_count} review{company.google_review_count === 1 ? "" : "s"})
                        </span>
                      )}
                    </dd>
                  </div>
                )}
                <div className="flex items-center justify-between border-t border-border/40 pt-2">
                  <dt className="text-muted-foreground">Lead score</dt>
                  <dd>
                    <ScoreBadge score={company.lead_score} />
                  </dd>
                </div>
                <div className="flex justify-between border-t border-border/40 pt-2">
                  <dt className="text-muted-foreground">Source</dt>
                  <dd>{company.source === "google_places" ? "Google Places" : "CSV upload"}</dd>
                </div>
              </dl>
            </section>

            {hasSocial && (
              <section>
                <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Social links</p>
                <div className="flex gap-2">
                  {social.linkedin && (
                    <a
                      href={social.linkedin}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="LinkedIn"
                      className="rounded-lg border border-border p-2.5 transition hover:border-primary/50 hover:bg-primary/5"
                    >
                      <Linkedin className="h-4 w-4" />
                    </a>
                  )}
                  {social.twitter && (
                    <a
                      href={social.twitter}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="Twitter / X"
                      className="rounded-lg border border-border p-2.5 transition hover:border-primary/50 hover:bg-primary/5"
                    >
                      <Twitter className="h-4 w-4" />
                    </a>
                  )}
                  {social.instagram && (
                    <a
                      href={social.instagram}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="Instagram"
                      className="rounded-lg border border-border p-2.5 transition hover:border-primary/50 hover:bg-primary/5"
                    >
                      <Instagram className="h-4 w-4" />
                    </a>
                  )}
                  {social.facebook && (
                    <a
                      href={social.facebook}
                      target="_blank"
                      rel="noopener noreferrer"
                      title="Facebook"
                      className="rounded-lg border border-border p-2.5 transition hover:border-primary/50 hover:bg-primary/5"
                    >
                      <Facebook className="h-4 w-4" />
                    </a>
                  )}
                </div>
              </section>
            )}

            {company.summary && (
              <section className="rounded-xl border border-primary/20 bg-primary/5 p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-primary">Summary</p>
                <p className="mt-2 text-sm leading-relaxed">{company.summary}</p>
              </section>
            )}

            {company.tech_stack_signals && company.tech_stack_signals.length > 0 && (
              <section>
                <p className="mb-2 text-xs font-medium uppercase text-muted-foreground">Tech stack signals</p>
                <div className="flex flex-wrap gap-2">
                  {company.tech_stack_signals.map((s) => (
                    <span key={s} className="rounded-full border border-border bg-muted/40 px-2.5 py-1 text-xs">
                      {s}
                    </span>
                  ))}
                </div>
              </section>
            )}

            <section>
              <p className="mb-3 text-xs font-medium uppercase text-muted-foreground">
                Executives ({executives.length})
              </p>
              {executives.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No named executives found on the company website. Social icons and nav links are excluded.
                </p>
              ) : (
                <div className="space-y-3">
                  {executives.map((exec) => (
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
                            <div className="flex shrink-0 flex-col items-end gap-1">
                              {confidenceBadge(exec.extraction_confidence)}
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
                          </div>
                          <div className="mt-3 flex flex-wrap items-center gap-2">
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
                              <a
                                href={`tel:${exec.phone}`}
                                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                              >
                                <Phone className="h-3 w-3" /> {exec.phone}
                              </a>
                            )}
                            {exec.linkedin_url && (
                              <a
                                href={exec.linkedin_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                title="LinkedIn profile"
                                className="inline-flex items-center rounded-md border border-border p-1.5 hover:border-primary/50 hover:bg-primary/5"
                              >
                                <Linkedin className="h-3.5 w-3.5" />
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </motion.aside>
      </>
    </AnimatePresence>
  );
}
