import { API_BASE } from "../lib/runtime";
export const fetchApi = (path: string) => fetch(`${API_BASE}${path}`);

