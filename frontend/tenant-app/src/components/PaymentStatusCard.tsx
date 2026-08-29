import { Card, CardContent } from "@/components/ui/card";
import { Receipt as ReceiptIcon, CheckCircle2, AlertCircle, Clock, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  getPaymentState,
  getGrandTotal,
  getAmountReceived,
  getRemainingAmount,
  formatCurrency,
} from "@/lib/utils";
import type { Receipt, PaymentState } from "@/types";

const statusConfig: Record<
  PaymentState,
  {
    label: string;
    color: string;
    bg: string;
    border: string;
    barColor: string;
    icon: React.ComponentType<{ className?: string }>;
  }
> = {
  PAID: {
    label: "Paid",
    color: "text-emerald-600",
    bg: "bg-emerald-500/5",
    border: "border-emerald-500/20",
    barColor: "bg-emerald-500",
    icon: CheckCircle2,
  },
  ADVANCE: {
    label: "Advance Paid",
    color: "text-cyan-600",
    bg: "bg-cyan-500/5",
    border: "border-cyan-500/20",
    barColor: "bg-cyan-500",
    icon: TrendingUp,
  },
  PARTIAL: {
    label: "Partial",
    color: "text-amber-600",
    bg: "bg-amber-500/5",
    border: "border-amber-500/20",
    barColor: "bg-amber-500",
    icon: AlertCircle,
  },
  PENDING: {
    label: "Pending",
    color: "text-red-600",
    bg: "bg-red-500/5",
    border: "border-red-500/20",
    barColor: "bg-red-500",
    icon: Clock,
  },
};

export default function PaymentStatusCard({
  receipts,
  outstandingBalance,
}: {
  receipts: Receipt[];
  outstandingBalance?: number;
}) {
  const active = receipts.filter((r) => r.Status !== "ARCHIVED");

  if (active.length === 0) {
    return (
      <Card className="rounded-2xl border border-dashed shadow-sm">
        <CardContent className="p-6 text-center">
          <ReceiptIcon className="mx-auto h-8 w-8 text-muted-foreground/50 mb-2" />
          <p className="text-sm text-muted-foreground">No active receipts yet</p>
        </CardContent>
      </Card>
    );
  }

  const sorted = [...active].sort(
    (a, b) => new Date(b.Date || 0).getTime() - new Date(a.Date || 0).getTime()
  );
  const latest = sorted[0];
  const state = getPaymentState(latest);
  const config = statusConfig[state];
  const Icon = config.icon;

  const grandTotal = getGrandTotal(latest);
  const received = getAmountReceived(latest);
  const remaining = getRemainingAmount(latest);
  const progress = grandTotal > 0 ? Math.min(100, (received / grandTotal) * 100) : 0;

  const totalOutstanding =
    outstandingBalance !== undefined
      ? outstandingBalance
      : active
          .filter((r) => {
            const s = getPaymentState(r);
            return s === "PENDING" || s === "PARTIAL";
          })
          .reduce((sum, r) => sum + getRemainingAmount(r), 0);

  return (
    <Card className={cn("rounded-2xl border shadow-sm", config.bg, config.border)}>
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1">
              Latest Receipt — {latest.Month}
            </p>
            <div className="flex items-center gap-2">
              <Icon className={cn("h-5 w-5", config.color)} />
              <h3 className={cn("text-xl font-bold", config.color)}>{config.label}</h3>
            </div>
          </div>
          <span className="text-xs font-medium text-muted-foreground">Bill {latest.Bill}</span>
        </div>

        <div className="mb-3">
          <div className="flex justify-between text-sm mb-1.5">
            <span className="text-muted-foreground">
              {state === "PENDING" && (
                <>Amount Due: <span className="font-semibold text-foreground">{formatCurrency(grandTotal)}</span></>
              )}
              {state === "PARTIAL" && (
                <>Remaining: <span className="font-semibold text-foreground">{formatCurrency(remaining)}</span></>
              )}
              {state === "PAID" && (
                <span className="text-emerald-600 font-medium">Fully Paid</span>
              )}
              {state === "ADVANCE" && (
                <>Advance: <span className="font-semibold text-foreground">{formatCurrency(received - grandTotal)}</span></>
              )}
            </span>
            <span className="text-muted-foreground">{Math.round(progress)}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-border overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all duration-500", config.barColor)}
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>Paid: {formatCurrency(received)}</span>
            <span>Total: {formatCurrency(grandTotal)}</span>
          </div>
        </div>

        {totalOutstanding > 0 && state !== "PENDING" && (
          <div className="pt-3 border-t border-border/50">
            <p className="text-xs text-muted-foreground">
              Total outstanding:{" "}
              <span className="font-semibold text-foreground">{formatCurrency(totalOutstanding)}</span>
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
