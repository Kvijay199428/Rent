import en from "react-phone-number-input/locale/en.json";

type CountryNameMap = Record<string, string>;

const NAMES = en as CountryNameMap;

export function getCountryName(code?: string): string {
  if (!code) return "";
  return NAMES[code] ?? code;
}

export interface CountryOption {
  code: string;
  name: string;
}

export const COUNTRY_OPTIONS: CountryOption[] = Object.entries(NAMES)
  .filter(([code, name]) => code && typeof name === "string")
  .map(([code, name]) => ({ code, name }))
  .sort((a, b) => a.name.localeCompare(b.name));
