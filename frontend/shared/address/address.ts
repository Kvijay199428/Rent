export interface StructuredAddress {
  flatNo?: string;
  floor?: string;
  street?: string;
  block?: string;
  locality?: string;
  city?: string;
  pinCode?: string;
  state?: string;
  country?: string;
}

export const EMPTY_ADDRESS: StructuredAddress = {
  flatNo: '',
  floor: '',
  street: '',
  block: '',
  locality: '',
  city: '',
  pinCode: '',
  state: '',
  country: '',
};

export function isStructuredAddress(value: unknown): value is StructuredAddress {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
