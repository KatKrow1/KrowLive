"use client";

import { createContext, useContext, useState } from "react";

type Country = "CA" | "AU";

type AppContextValue = {
  country: Country;
  setCountry: (c: Country) => void;
  search: string;
  setSearch: (s: string) => void;
};

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [country, setCountry] = useState<Country>("CA");
  const [search, setSearch] = useState("");
  return (
    <AppContext.Provider value={{ country, setCountry, search, setSearch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppContext must be used within AppProvider");
  return ctx;
}
