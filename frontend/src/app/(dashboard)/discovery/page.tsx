"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Loader2, MapPin, Radar, Sparkles } from "lucide-react";
import { api, JobStatus } from "@/lib/api";
import { useAppContext } from "@/lib/context";
import { AU_CITIES, AU_STATES, CA_CITIES, CA_PROVINCES, INDUSTRIES } from "@/lib/constants";
import { cn } from "@/lib/utils";

const STEPS = ["Industry", "Location", "Review & Run"];

export default function DiscoveryPage() {
  const { country } = useAppContext();
  const [step, setStep] = useState(0);
  const [industry, setIndustry] = useState("Media");
  const [customIndustry, setCustomIndustry] = useState("");
  const [selectedStates, setSelectedStates] = useState<string[]>(country === "CA" ? ["Ontario"] : ["NSW"]);
  const [maxResults, setMaxResults] = useState(3);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const states = country === "CA" ? [...CA_PROVINCES] : [...AU_STATES];
  const cityMap = country === "CA" ? CA_CITIES : AU_CITIES;
  const resolvedIndustry = industry === "Custom" ? customIndustry.trim() : industry;

  useEffect(() => {
    setSelectedStates(country === "CA" ? ["Ontario"] : ["NSW"]);
  }, [country]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | undefined;
    const poll = async () => {
      try {
        const status = await api.getStatus();
        setJobStatus(status);
        if (status.status === "running") {
          if (!interval) interval = setInterval(poll, 2000);
        } else if (interval) {
          clearInterval(interval);
          setRunning(false);
        }
      } catch {
        /* ignore */
      }
    };
    poll();
    return () => {
      if (interval) clearInterval(interval);
    };
  }, []);

  const cities = selectedStates.flatMap((s) => cityMap[s] ?? []);

  const run = async () => {
    setError(null);
    setRunning(true);
    try {
      await api.runDiscovery({
        industry: resolvedIndustry,
        country,
        states: selectedStates,
        cities,
        max_results: maxResults,
      });
      setJobStatus(await api.getStatus());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Discovery failed");
      setRunning(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <Radar className="h-6 w-6 text-primary" />
          Discovery
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Find media &amp; marketing companies via Google Places, scrape websites, and enrich leads.
        </p>
        <p className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-200/90">
          Scraped contact data must be verified for consent before commercial email outreach under
          CASL/Spam Act requirements.
        </p>
      </div>

      <div className="flex gap-2">
        {STEPS.map((label, i) => (
          <div
            key={label}
            className={cn(
              "flex flex-1 items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium",
              i === step ? "border-primary/50 bg-primary/10 text-primary" : "border-border text-muted-foreground",
              i < step && "border-success/30 text-success"
            )}
          >
            {i < step ? <Check className="h-3.5 w-3.5" /> : <span>{i + 1}</span>}
            {label}
          </div>
        ))}
      </div>

      <motion.div layout className="glass rounded-xl p-6 shadow-soft">
        <AnimatePresence mode="wait">
          {step === 0 && (
            <motion.div key="s0" initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }} className="space-y-4">
              <h2 className="flex items-center gap-2 font-medium">
                <Sparkles className="h-4 w-4 text-primary" /> Choose industry
              </h2>
              <div className="flex flex-wrap gap-2">
                {INDUSTRIES.map((item) => (
                  <button
                    key={item}
                    type="button"
                    onClick={() => setIndustry(item)}
                    className={cn(
                      "rounded-lg border px-3 py-2 text-sm transition",
                      industry === item ? "border-primary bg-primary/15 text-primary" : "border-border hover:border-primary/40"
                    )}
                  >
                    {item}
                  </button>
                ))}
              </div>
              {industry === "Custom" && (
                <input
                  className="w-full rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm"
                  placeholder="Custom industry"
                  value={customIndustry}
                  onChange={(e) => setCustomIndustry(e.target.value)}
                />
              )}
            </motion.div>
          )}

          {step === 1 && (
            <motion.div key="s1" initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }} className="space-y-4">
              <h2 className="flex items-center gap-2 font-medium">
                <MapPin className="h-4 w-4 text-primary" /> Choose location
              </h2>
              <p className="text-sm text-muted-foreground">{country === "CA" ? "Provinces" : "States"}</p>
              <div className="flex flex-wrap gap-2">
                {states.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() =>
                      setSelectedStates((prev) =>
                        prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
                      )
                    }
                    className={cn(
                      "rounded-lg border px-3 py-2 text-sm",
                      selectedStates.includes(s) ? "border-accent/50 bg-accent/10 text-accent" : "border-border"
                    )}
                  >
                    {s}
                  </button>
                ))}
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Max results per city</label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={maxResults}
                  onChange={(e) => setMaxResults(Number(e.target.value))}
                  className="mt-1 w-24 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm"
                />
              </div>
            </motion.div>
          )}

          {step === 2 && (
            <motion.div key="s2" initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }} className="space-y-4">
              <h2 className="font-medium">Review &amp; run</h2>
              <dl className="grid gap-2 text-sm">
                <div className="flex justify-between border-b border-border/60 py-2">
                  <dt className="text-muted-foreground">Industry</dt>
                  <dd>{resolvedIndustry || "—"}</dd>
                </div>
                <div className="flex justify-between border-b border-border/60 py-2">
                  <dt className="text-muted-foreground">Country</dt>
                  <dd>{country}</dd>
                </div>
                <div className="flex justify-between border-b border-border/60 py-2">
                  <dt className="text-muted-foreground">Regions</dt>
                  <dd>{selectedStates.join(", ") || "—"}</dd>
                </div>
                <div className="flex justify-between py-2">
                  <dt className="text-muted-foreground">Cities</dt>
                  <dd>{cities.join(", ") || "—"}</dd>
                </div>
              </dl>

              {jobStatus?.status === "running" && (
                <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
                  <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {jobStatus.message || "Running…"}
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <motion.div
                      className="h-full bg-gradient-to-r from-primary to-accent"
                      animate={{ width: `${jobStatus.progress}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {jobStatus.processed_items}/{jobStatus.total_items} processed · {jobStatus.progress}%
                  </p>
                </div>
              )}

              {error && <p className="text-sm text-red-400">{error}</p>}
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-6 flex justify-between">
          <button
            type="button"
            disabled={step === 0 || running}
            onClick={() => setStep((s) => s - 1)}
            className="rounded-lg border border-border px-4 py-2 text-sm disabled:opacity-40"
          >
            Back
          </button>
          {step < 2 ? (
            <button
              type="button"
              onClick={() => setStep((s) => s + 1)}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white"
            >
              Continue
            </button>
          ) : (
            <button
              type="button"
              disabled={running || !resolvedIndustry || selectedStates.length === 0}
              onClick={run}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {running && <Loader2 className="h-4 w-4 animate-spin" />}
              Run Discovery
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );
}
