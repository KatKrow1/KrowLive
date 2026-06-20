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
