import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Eye, Receipt as ReceiptIcon } from "lucide-react";
import { cn, getPaymentState, getGrandTotal, getAmountReceived, formatCurrency, isSettled } from "@/lib/utils";
import type { Receipt, PaymentState } from "@/types";

const statusStyles: Record<PaymentState, string> = {
  PAID: "bg-emerald-500/10 text-emerald-600",
  ADVANCE: "bg-cyan-500/10 text-cyan-600",
  PARTIAL: "bg-amber-500/10 text-amber-600",
  PENDING: "bg-red-500/10 text-red-600",
};

const statusLabels: Record<PaymentState, string> = {
  PAID: "Paid",
  ADVANCE: "Advance",
  PARTIAL: "Partial",
  PENDING: "Pending",
};

export function ReceiptRoller({
  receipts,
  onViewPdf,
}: {
  receipts: Receipt[];
  onViewPdf?: (billNo: string) => void;
}) {
  if (receipts.length === 0) return null;

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {receipts.map((r) => {
        const state = isSettled(r) ? "PAID" : getPaymentState(r);
        const grandTotal = getGrandTotal(r);
        const received = getAmountReceived(r);
        return (
          <Card key={r.Bill} className="rounded-2xl border shadow-sm overflow-hidden">
            <CardContent className="p-4">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2.5">
                  <div className="h-8 w-8 rounded-lg bg-muted flex items-center justify-center">
                    <ReceiptIcon className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div>
                    <span className="font-semibold text-sm">{r.Month}</span>
                    <p className="text-xs text-muted-foreground">
                      {r.Bill} &middot; {r.Date}
                    </p>
                  </div>
                </div>
                <Badge variant="outline" className={cn("shrink-0 text-[10px]", statusStyles[state])}>
                  {isSettled(r) ? "Settled" : statusLabels[state]}
                </Badge>
              </div>

              <div className="flex items-center justify-between text-sm mt-3">
                <span className="text-muted-foreground">
                  Total: <span className="font-semibold text-foreground">{formatCurrency(grandTotal)}</span>
                </span>
                {isSettled(r) ? (
                  <span className="text-muted-foreground">
                    Cleared by <span className="font-semibold text-foreground">{r.settledByBill}</span>
                  </span>
                ) : state !== "PAID" && state !== "ADVANCE" ? (
                  <span className="text-muted-foreground">
                    Paid: <span className="font-semibold text-foreground">{formatCurrency(received)}</span>
                  </span>
                ) : null}
              </div>

              <Button
                variant="outline"
                size="sm"
                className="w-full mt-3"
                onClick={() => onViewPdf?.(r.Bill)}
              >
                <Eye className="h-3.5 w-3.5 mr-1.5" />
                View PDF
              </Button>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
