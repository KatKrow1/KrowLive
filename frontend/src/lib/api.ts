import { API_URL } from "./constants";

export type SocialLinks = {
  linkedin?: string | null;
  twitter?: string | null;
  instagram?: string | null;
  facebook?: string | null;
};

export type LeadStatus = "new" | "contacted" | "replied" | "not_interested";

export type Executive = {
  id?: string;
  company_id?: string | null;
  name: string;
  title?: string | null;
  email?: string | null;
  phone?: string | null;
  linkedin_url?: string | null;
  consent_status: "unknown" | "opted_in" | "opted_out";
  extraction_confidence?: "high" | "medium" | "low";
  source_url?: string | null;
  scraped_at?: string | null;
};

/** Full company — id is UUID string; country_id/state_id are integers. */
export type Company = {
  id?: string;
  name: string;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  country: "CA" | "AU";
  country_id?: number | null;
  state_id?: number | null;
  state_slug?: string | null;
  phone?: string | null;
  website: string;
  google_rating?: number | null;
  google_review_count?: number | null;
  lead_score?: number | null;
  summary?: string | null;
  tech_stack_signals?: string[];
  source: "google_places" | "csv_upload";
  social_links?: SocialLinks;
  executives?: Executive[];
  last_scraped_at?: string | null;
  source_url?: string | null;
  lead_status?: LeadStatus;
};

export type CompanySummary = {
  id: string;
  name: string;
  website?: string | null;
  lead_score?: number | null;
  lead_status?: LeadStatus;
  last_scraped_at?: string | null;
};

export type SavedSearch = {
  id: string;
  name: string;
  industry: string;
  country: "CA" | "AU";
  states: string[];
  cities: string[];
  max_results: number;
  created_at?: string | null;
  last_run_at?: string | null;
  last_result_count: number;
};

export type SavedSearchRunResult = {
  saved_search_id: string;
  new_companies: CompanySummary[];
  new_count: number;
  total_processed: number;
};

export type Webhook = {
  id: string;
  url: string;
  active: boolean;
  created_at?: string | null;
};

export type CompanyDetailResponse = {
  company: Company;
  executives: Executive[];
};

export type JobStatus = {
  status: "idle" | "running" | "completed" | "failed";
  progress: number;
  message?: string | null;
  total_items: number;
  processed_items: number;
  error?: string | null;
};

export type StateChartPoint = { state: string; count: number };

export type Stats = {
  total_companies: number;
  avg_lead_score: number;
  canada_count: number;
  australia_count: number;
  chart_by_state: StateChartPoint[];
};

export type CountryNode = {
  id: number;
  code: "CA" | "AU";
  name: string;
};

export type StateNode = {
  id: number;
  name: string;
  slug: string;
};

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
  getCountries: () => request<CountryNode[]>("/countries"),
  getStates: (countryId: number | string) =>
    request<StateNode[]>(`/countries/${countryId}/states`),
  getCompanies: (stateId: number) => request<CompanySummary[]>(`/states/${stateId}/companies`),
  getCompany: (id: string) => request<CompanyDetailResponse>(`/companies/${id}`),
  getStats: (country?: "CA" | "AU") =>
    request<Stats>(`/stats${country ? `?country=${country}` : ""}`),
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

  exportCompaniesCsv: (params: Record<string, string | number | undefined>) => {
    const qs = new URLSearchParams();
    qs.set("format", "csv");
    Object.entries(params).forEach(([k, v]) => {
      if (v != null && v !== "") qs.set(k, String(v));
    });
    const url = `${API_URL}/companies/export?${qs.toString()}`;
    return fetch(url).then(async (res) => {
      if (!res.ok) throw new ApiError(`Export failed (${res.status})`, url);
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "krowlive-companies.csv";
      a.click();
      URL.revokeObjectURL(a.href);
    });
  },

  updateCompanyStatus: (id: string, status: LeadStatus) =>
    request<{ company_id: string; status: LeadStatus }>(`/companies/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }),

  bulkUpdateStatus: (company_ids: string[], status: LeadStatus) =>
    request<{ updated: number; status: LeadStatus }>("/companies/status/bulk", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_ids, status }),
    }),

  rescrapeCompany: (id: string) =>
    request<CompanyDetailResponse>(`/companies/${id}/rescrape`, { method: "POST" }),

  getSavedSearches: () => request<SavedSearch[]>("/saved-searches"),
  createSavedSearch: (body: Omit<SavedSearch, "id" | "last_run_at" | "last_result_count" | "created_at">) =>
    request<SavedSearch>("/saved-searches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  runSavedSearch: (id: string) =>
    request<SavedSearchRunResult>(`/saved-searches/${id}/run`, { method: "POST" }),
  deleteSavedSearch: (id: string) =>
    request<{ deleted: string }>(`/saved-searches/${id}`, { method: "DELETE" }),

  getWebhooks: () => request<Webhook[]>("/integrations/webhooks"),
  createWebhook: (url: string) =>
    request<Webhook>("/integrations/webhook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    }),
  deleteWebhook: (id: string) =>
    request<{ deleted: string }>(`/integrations/webhooks/${id}`, { method: "DELETE" }),
};
