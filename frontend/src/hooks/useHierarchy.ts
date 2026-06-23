import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export const hierarchyKeys = {
  countries: ["hierarchy", "countries"] as const,
  states: (countryId: number | string) => ["hierarchy", "states", countryId] as const,
  companies: (stateId: number) => ["hierarchy", "companies", stateId] as const,
  company: (id: number | string) => ["company", id] as const,
};

export function useCountries() {
  return useQuery({
    queryKey: hierarchyKeys.countries,
    queryFn: () => api.getCountries(),
  });
}

export function useStates(countryId: number | string) {
  return useQuery({
    queryKey: hierarchyKeys.states(countryId),
    queryFn: () => api.getStates(countryId),
    enabled: countryId !== "" && countryId != null,
  });
}

export function useCompanies(stateId: number | null) {
  return useQuery({
    queryKey: hierarchyKeys.companies(stateId ?? 0),
    queryFn: () => api.getCompanies(stateId!),
    enabled: stateId != null,
  });
}

export function useCompany(id: string | null) {
  return useQuery({
    queryKey: hierarchyKeys.company(id ?? ""),
    queryFn: async () => {
      const data = await api.getCompany(id!);
      return {
        ...data.company,
        executives: data.executives,
      };
    },
    enabled: Boolean(id),
  });
}

/** Resolve state slug from URL to numeric state id using country code. */
export function useStateId(countryCode: string, stateSlug: string) {
  const query = useStates(countryCode);
  const state = query.data?.find((s) => s.slug === stateSlug);
  return {
    stateId: state?.id ?? null,
    state,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
  };
}
