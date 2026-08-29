import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import type { Receipt, PaymentState } from "@/types"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ── Date helpers ──────────────────────────────────────────

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export function parseMonthYear(monthStr: string): Date {
  const parts = monthStr.trim().split(" ");
  if (parts.length !== 2) return new Date(0);
  const monthIndex = MONTH_NAMES.indexOf(parts[0]);
  const year = parseInt(parts[1], 10);
  if (monthIndex === -1 || isNaN(year)) return new Date(0);
  return new Date(year, monthIndex, 1);
}

export function getMonthEndDate(monthStr: string): Date {
  const d = parseMonthYear(monthStr);
  return new Date(d.getFullYear(), d.getMonth() + 1, 0);
}

export function isOlderThan12Months(monthStr: string): boolean {
  const receiptDate = parseMonthYear(monthStr);
  const now = new Date();
  const cutoff = new Date(now.getFullYear(), now.getMonth() - 12, 1);
  return receiptDate < cutoff;
}

export function daysResided(residentSince: string): number {
  const start = new Date(`${residentSince}T00:00:00`);
  if (Number.isNaN(start.getTime())) return 0;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.max(0, Math.floor((today.getTime() - start.getTime()) / 86_400_000));
}

export function daysInMonth(residentSince: string, monthStr: string): number {
  const monthStart = parseMonthYear(monthStr);
  const monthEnd = getMonthEndDate(monthStr);
  const start = new Date(`${residentSince}T00:00:00`);
  if (Number.isNaN(start.getTime()) || start > monthEnd) return 0;
  const effectiveStart = start > monthStart ? start : monthStart;
  return Math.max(0, Math.ceil((monthEnd.getTime() - effectiveStart.getTime()) / 86_400_000));
}

// ── Currency ──────────────────────────────────────────────

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

// ── Payment helpers ───────────────────────────────────────

export function getPaymentState(receipt: Receipt): PaymentState {
  const total = Number(receipt.Total ?? 0);
  const arrears = Number(receipt.previousArrears ?? 0);
  const received = Number(receipt.amountReceived ?? 0);
  const payable = total + arrears;
  const stored = String(receipt.paymentStatus ?? "").toUpperCase();

  if (stored === "ADVANCE" || received > payable) return "ADVANCE";
  if (stored === "PARTIAL" || (received > 0 && received < payable)) return "PARTIAL";
  if (stored === "PAID" || received >= payable) return "PAID";
  return "PENDING";
}

export function getGrandTotal(receipt: Receipt): number {
  return Number(receipt.Total ?? 0) + Number(receipt.previousArrears ?? 0);
}

export function getAmountReceived(receipt: Receipt): number {
  return Number(receipt.amountReceived ?? 0);
}

export function getRemainingAmount(receipt: Receipt): number {
  return Math.max(0, getGrandTotal(receipt) - getAmountReceived(receipt));
}

/** True when a bill was cleared by a later payment (settled_by_bill_no set). */
export function isSettled(receipt: Receipt): boolean {
  const s = String(receipt.settlementType ?? "").toUpperCase();
  return !!receipt.settledByBill && (s === "CURRENT_PAYMENT" || s === "ARREAR");
}

export function formatResidentSince(dateStr: string): string {
  if (!dateStr) return "—";
  const d = new Date(`${dateStr}T00:00:00`);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}
