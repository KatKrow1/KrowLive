import { API_URL } from "./constants";

export type SocialLinks = {
  linkedin?: string | null;
  twitter?: string | null;
  instagram?: string | null;
  facebook?: string | null;
};

export type Executive = {
  id?: string;
  name: string;
  title?: string | null;
  email?: string | null;
  phone?: string | null;
  linkedin_url?: string | null;
  consent_status: "unknown" | "opted_in" | "opted_out";
  extraction_confidence?: "high" | "medium" | "low";
};

export type Company = {
  id?: string;
  name: string;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  country: "CA" | "AU";
  phone?: string | null;
  website: string;
  category?: string | null;
  google_rating?: number | null;
  google_review_count?: number | null;
  lead_score?: number | null;
  summary?: string | null;
  tech_stack_signals?: string[];
  source: "google_places" | "csv_upload";
  social_links?: SocialLinks;
  executives?: Executive[];
};

export type CompanyListResponse = {
  items: Company[];
  total: number;
  page: number;
  page_size: number;
};

export type JobStatus = {
  status: "idle" | "running" | "completed" | "failed";
  progress: number;
  message?: string | null;
  total_items: number;
  processed_items: number;
  error?: string | null;
};

export type Stats = {
  total_companies: number;
  avg_lead_score: number;
  canada_count: number;
  australia_count: number;
  top_industry: string;
};

export type StateChartPoint = { state: string; count: number };

export type CsvUploadResult = {
  rows_processed: number;
  rows_new: number;
  rows_updated: number;
  errors: string[];
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly url: string,
    public readonly cause?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_URL}${path}`;
  try {
    const res = await fetch(url, init);
    if (!res.ok) {
      const text = await res.text();
      const msg = `[KrowLive API] ${init?.method ?? "GET"} ${url} failed (${res.status}): ${text || res.statusText}`;
      console.error(msg);
      throw new ApiError(msg, url);
    }
    return res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    const msg =
      err instanceof TypeError && err.message === "Failed to fetch"
        ? `[KrowLive API] Network error — cannot reach backend at ${API_URL}. Is uvicorn running? CORS may also block this origin (${typeof window !== "undefined" ? window.location.origin : "unknown"}).`
        : `[KrowLive API] ${init?.method ?? "GET"} ${url} failed: ${err instanceof Error ? err.message : String(err)}`;
    console.error(msg, err);
    throw new ApiError(msg, url, err);
  }
}

export const api = {
  getStats: (country?: "CA" | "AU") =>
    request<Stats>(`/companies/stats${country ? `?country=${country}` : ""}`),
  getChartByState: (country?: "CA" | "AU") =>
    request<StateChartPoint[]>(`/companies/chart/by-state${country ? `?country=${country}` : ""}`),
  getCompanies: (params: Record<string, string | number | undefined>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return request<CompanyListResponse>(`/companies?${qs.toString()}`);
  },
  getCompany: (id: string) => request<Company>(`/companies/${id}`),
  getStatus: () => request<JobStatus>("/status"),
  runDiscovery: (body: object) =>
    request<JobStatus>("/discovery/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  uploadCsv: async (file: File) => {
    const url = `${API_URL}/upload/csv`;
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(url, { method: "POST", body: form });
      if (!res.ok) {
        const text = await res.text();
        const msg = `[KrowLive API] POST ${url} failed (${res.status}): ${text}`;
        console.error(msg);
        throw new ApiError(msg, url);
      }
      return res.json() as Promise<CsvUploadResult>;
    } catch (err) {
      if (err instanceof ApiError) throw err;
      const msg = `[KrowLive API] POST ${url} failed: ${err instanceof Error ? err.message : String(err)}`;
      console.error(msg, err);
      throw new ApiError(msg, url, err);
    }
  },
  getLastCsvResult: () => request<CsvUploadResult>("/upload/csv/last"),
};
