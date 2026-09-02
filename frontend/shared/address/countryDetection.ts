import { getApiUrl } from "@shared/api-config";

export const DEFAULT_COUNTRY = "IN";

export async function detectCountry(): Promise<string> {
  try {
    const res = await fetch(getApiUrl("/api/location/country"), {
      credentials: "include",
    });
    if (res.ok) {
      const data = await res.json();
      if (data?.country && typeof data.country === "string") {
        return data.country.toUpperCase();
      }
    }
  } catch {
    // fall through to default
  }
  return DEFAULT_COUNTRY;
}
