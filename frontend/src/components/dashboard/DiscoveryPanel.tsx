"use client";

import { useEffect, useState } from "react";
import { Loader2, Radar } from "lucide-react";
import { api, JobStatus } from "@/lib/api";
import { AU_STATES, CA_PROVINCES, citiesForStates, defaultCitiesForCountry, defaultStatesForCountry, INDUSTRIES } from "@/lib/constants";
import { cn } from "@/lib/utils";

type DiscoveryPanelProps = {
  country: "CA" | "AU";
  jobStatus: JobStatus | null;
  onStarted: () => void;
};

export function DiscoveryPanel({ country, jobStatus, onStarted }: DiscoveryPanelProps) {
  const [industry, setIndustry] = useState("Media");
  const [customIndustry, setCustomIndustry] = useState("");
  const [selectedStates, setSelectedStates] = useState<string[]>(() => defaultStatesForCountry(country));
  const [selectedCities, setSelectedCities] = useState<string[]>(() => defaultCitiesForCountry(country));
  const [maxResults, setMaxResults] = useState(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const states = country === "CA" ? [...CA_PROVINCES] : [...AU_STATES];

  useEffect(() => {
    setSelectedStates(defaultStatesForCountry(country));
    setSelectedCities(defaultCitiesForCountry(country));
  }, [country]);

  const availableCities = citiesForStates(country, selectedStates);

  useEffect(() => {
    setSelectedCities((prev) => {
      const kept = prev.filter((c) => availableCities.includes(c));
      return kept.length > 0 ? kept : availableCities;
    });
  }, [selectedStates, country, availableCities.join("|")]);

  const toggleState = (state: string) => {
    setSelectedStates((prev) =>
      prev.includes(state) ? prev.filter((s) => s !== state) : [...prev, state]
    );
  };

  const toggleCity = (city: string) => {
    setSelectedCities((prev) =>
      prev.includes(city) ? prev.filter((c) => c !== city) : [...prev, city]
    );
  };

  const resolvedIndustry = industry === "Custom" ? customIndustry.trim() : industry;
  const running = jobStatus?.status === "running" || loading;

  const runDiscovery = async () => {
    if (!resolvedIndustry) {
      setError("Please select or enter an industry");
      return;
    }
    if (selectedStates.length === 0) {
      setError("Select at least one province/state");
      return;
    }
    const cities = selectedCities.filter((c) => availableCities.includes(c));
    if (cities.length === 0) {
      setError("Select at least one city");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await api.runDiscovery({
        industry: resolvedIndustry,
        country,
        states: selectedStates,
        cities,
        max_results: maxResults,
      });
      onStarted();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Discovery failed");
      console.error("[KrowLive] Discovery run failed:", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="mb-4 flex items-center gap-2">
        <Radar className="h-5 w-5 text-violet-400" />
        <h2 className="text-lg font-semibold">Run Discovery</h2>
      </div>

      <p className="mb-4 text-xs leading-relaxed text-amber-200/80">
        Scraped contact data must be verified for consent before commercial email outreach under
        CASL/Spam Act requirements.
      </p>

      <div className="space-y-4">
        <div>
          <label className="mb-2 block text-sm text-muted-foreground">Industry</label>
          <div className="flex flex-wrap gap-2">
            {[...INDUSTRIES].map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setIndustry(item)}
                className={cn(
                  "rounded-lg border px-3 py-1.5 text-sm transition",
                  industry === item
                    ? "border-violet-500 bg-violet-500/20 text-violet-200"
                    : "border-border bg-muted/40 text-muted-foreground hover:border-violet-500/40"
                )}
              >
                {item}
              </button>
            ))}
          </div>
          {industry === "Custom" && (
            <input
              className="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              placeholder="Enter custom industry"
              value={customIndustry}
              onChange={(e) => setCustomIndustry(e.target.value)}
            />
          )}
        </div>

        <div>
          <label className="mb-2 block text-sm text-muted-foreground">
            {country === "CA" ? "Provinces" : "States"} (multi-select)
          </label>
          <div className="flex flex-wrap gap-2">
            {states.map((state) => (
              <button
                key={state}
                type="button"
                onClick={() => toggleState(state)}
                className={cn(
                  "rounded-lg border px-3 py-1.5 text-sm",
                  selectedStates.includes(state)
                    ? "border-fuchsia-500 bg-fuchsia-500/20 text-fuchsia-200"
                    : "border-border bg-muted/40 text-muted-foreground"
                )}
              >
                {state}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm text-muted-foreground">Cities (multi-select)</label>
          {availableCities.length === 0 ? (
            <p className="text-xs text-muted-foreground">Select a {country === "CA" ? "province" : "state"} first.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {availableCities.map((city) => (
                <button
                  key={city}
                  type="button"
                  onClick={() => toggleCity(city)}
                  className={cn(
                    "rounded-lg border px-3 py-1.5 text-sm",
                    selectedCities.includes(city)
                      ? "border-fuchsia-500 bg-fuchsia-500/20 text-fuchsia-200"
                      : "border-border bg-muted/40 text-muted-foreground"
                  )}
                >
                  {city}
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="mb-2 block text-sm text-muted-foreground">Max results per city</label>
          <input
            type="number"
            min={1}
            max={20}
            value={maxResults}
            onChange={(e) => setMaxResults(Number(e.target.value))}
            className="w-24 rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        {jobStatus?.status === "running" && (
          <div>
            <div className="mb-1 flex justify-between text-xs text-muted-foreground">
              <span>{jobStatus.message}</span>
              <span>{jobStatus.progress}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all"
                style={{ width: `${jobStatus.progress}%` }}
              />
            </div>
          </div>
        )}

        <button
          type="button"
          disabled={running}
          onClick={runDiscovery}
          className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500 disabled:opacity-50"
        >
          {running && <Loader2 className="h-4 w-4 animate-spin" />}
          Run Discovery
        </button>
      </div>
    </div>
  );
}
