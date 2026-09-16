/**
 * Payment status math — frontend mirror of backend payment_status_engine.py.
 *
 * The backend engine is the single authority on payment status. The UI must
 * never derive statuses differently, or the amounts shown in live previews
 * will disagree with what gets stored. Mirror derive_status/round2/_norm
 * exactly so both sides agree within TOLERANCE (0.005).
 */

export const TOLERANCE = 0.005;

export const CANONICAL_PAYMENT_STATUSES = ["PENDING", "PARTIAL", "PAID", "ADVANCE"] as const;
export type PaymentStatus = (typeof CANONICAL_PAYMENT_STATUSES)[number];

/** Round an arbitrary value to 2dp; NaN/empty values become 0. */
export function round2(value: number | string | null | undefined): number {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return 0;
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

/** Coerce to float without rounding; bad values become 0. */
export function normAmount(value: number | string | null | undefined): number {
  const n = Number(value ?? 0);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Map (grand_total, received) to a canonical payment status.
 * Mirrors backend derive_status(): PENDING/ADVANCE/PAID/PARTIAL.
 */
export function deriveStatus(
  grandTotal: number | string | null | undefined,
  amountReceived: number | string | null | undefined,
  tolerance: number = TOLERANCE,
): PaymentStatus {
  const received = round2(amountReceived);
  if (received <= 0) return "PENDING";
  const derived = round2(received - round2(grandTotal));
  if (derived > tolerance) return "ADVANCE";
  if (Math.abs(derived) <= tolerance) return "PAID";
  return "PARTIAL";
}

/** grand_total = round2(bill_total + arrears), as the backend calculates it. */
export function grandTotalOf(
  billTotal: number | string | null | undefined,
  arrears: number | string | null | undefined,
): number {
  return round2(normAmount(billTotal) + normAmount(arrears));
}

/** SUM of active payment amounts, rounded — the backend's amount_received. */
export function receivedOf(amounts: Array<number | string | null | undefined>): number {
  return round2(amounts.reduce<number>((sum, a) => sum + normAmount(a), 0));
}