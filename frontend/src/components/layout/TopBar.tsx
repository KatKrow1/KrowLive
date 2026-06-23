"use client";

import { Search } from "lucide-react";
import { useAppContext } from "@/lib/context";
import { currencyForCountry } from "@/lib/constants";
import { cn } from "@/lib/utils";

export function TopBar() {
  const { country, setCountry, search, setSearch } = useAppContext();

  return (
    <header className="sticky top-0 z-30 flex items-center gap-4 border-b border-border/60 bg-background/80 px-4 py-3 backdrop-blur-xl md:px-6">
      <div className="md:hidden">
        <span className="bg-gradient-to-r from-violet-300 to-cyan-300 bg-clip-text text-lg font-bold text-transparent">
          KrowLive
        </span>
      </div>
      <div className="relative ml-auto flex-1 md:max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search companies globally…"
          className="w-full rounded-lg border border-border/80 bg-muted/40 py-2 pl-9 pr-3 text-sm transition focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>
      <div className="flex items-center gap-2 rounded-lg border border-border/80 bg-muted/30 p-1">
        {(["CA", "AU"] as const).map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => setCountry(c)}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-medium transition",
              country === c ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
            )}
          >
            {c === "CA" ? "Canada" : "Australia"}
          </button>
        ))}
      </div>
      <span className="hidden text-xs text-muted-foreground sm:inline">{currencyForCountry(country)}</span>
    </header>
  );
}
