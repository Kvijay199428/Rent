import { getApiUrl } from "@shared/api-config";

export const fetchApi = (path: string) => fetch(getApiUrl(`/rent/admin/api${path}`));

