export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const INDUSTRIES = [
  "Media",
  "Marketing Agency",
  "Advertising",
  "PR Firm",
  "Custom",
] as const;

export const CA_PROVINCES = [
  "Ontario",
  "British Columbia",
  "Alberta",
  "Quebec",
  "Manitoba",
  "Saskatchewan",
  "Nova Scotia",
  "New Brunswick",
] as const;

export const AU_STATES = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"] as const;

/** Long names for geocoding / display where abbreviations are used in the UI. */
export const AU_STATE_LABELS: Record<string, string> = {
  NSW: "New South Wales",
  VIC: "Victoria",
  QLD: "Queensland",
  WA: "Western Australia",
  SA: "South Australia",
  TAS: "Tasmania",
  ACT: "Australian Capital Territory",
  NT: "Northern Territory",
};

export function citiesForStates(
  country: "CA" | "AU",
  selectedStates: string[],
): string[] {
  const map = country === "CA" ? CA_CITIES : AU_CITIES;
  return selectedStates.flatMap((s) => map[s] ?? []);
}

export function defaultStatesForCountry(country: "CA" | "AU"): string[] {
  return country === "CA" ? ["Ontario"] : ["NSW"];
}

export function defaultCitiesForCountry(country: "CA" | "AU"): string[] {
  return citiesForStates(country, defaultStatesForCountry(country));
}

export const CA_CITIES: Record<string, string[]> = {
  Ontario: ["Toronto", "Ottawa"],
  "British Columbia": ["Vancouver"],
  Alberta: ["Calgary"],
  Quebec: ["Montreal"],
};

export const AU_CITIES: Record<string, string[]> = {
  NSW: ["Sydney"],
  VIC: ["Melbourne"],
  QLD: ["Brisbane"],
  WA: ["Perth"],
  SA: ["Adelaide"],
};

export function currencyForCountry(country: "CA" | "AU") {
  return country === "CA" ? "CAD" : "AUD";
}
