import type { StructuredAddress } from './address';
import { EMPTY_ADDRESS } from './address';

const LINE_SEPARATOR = ' | ';

function clean(value?: string): string {
  return (value ?? '').trim();
}

export function formatAddress(addr: StructuredAddress | string | null | undefined): string {
  if (typeof addr === 'string') {
    return addr.trim();
  }
  if (!addr || typeof addr !== 'object') {
    return '';
  }
  const parts = [
    clean(addr.flatNo),
    clean(addr.floor),
    clean(addr.street),
    clean(addr.block),
    clean(addr.locality),
    clean(addr.city),
    clean(addr.state),
    clean(addr.pinCode),
    clean(addr.country),
  ].filter(Boolean);
  return parts.join(LINE_SEPARATOR);
}

export function parseLegacyAddress(value?: string | null): StructuredAddress {
  if (!value) {
    return {};
  }
  const parts = value.split(LINE_SEPARATOR).map((p) => p.trim());
  const [flatNo, floor, street, block, locality, city, state, pinCode, country] = parts;
  return {
    flatNo,
    floor,
    street,
    block,
    locality,
    city,
    state,
    pinCode,
    country,
  };
}

export function serializeAddress(addr: StructuredAddress): string {
  return formatAddress(addr);
}

export function fromAddressFormValue(
  value: StructuredAddress | string | null | undefined
): StructuredAddress {
  if (typeof value === 'string') {
    return parseLegacyAddress(value);
  }
  if (value && typeof value === 'object') {
    return { ...EMPTY_ADDRESS, ...value };
  }
  return { ...EMPTY_ADDRESS };
}
