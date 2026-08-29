import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Archive, ChevronDown, ChevronUp, Download, Eye, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  getPaymentState,
  getGrandTotal,
  getAmountReceived,
  formatCurrency,
  isSettled,
  daysInMonth,
  formatResidentSince,
} from "@/lib/utils";
import { tenantApi } from "@/lib/api";
import type { Receipt, Occupant, PaymentState } from "@/types";

const statusStyles: Record<PaymentState, string> = {
  PAID: "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20",
  ADVANCE: "bg-cyan-500/10 text-cyan-600 hover:bg-cyan-500/20",
  PARTIAL: "bg-amber-500/10 text-amber-600 hover:bg-amber-500/20",
  PENDING: "bg-red-500/10 text-red-600 hover:bg-red-500/20",
};

const statusLabels: Record<PaymentState, string> = {
  PAID: "Paid",
  ADVANCE: "Advance",
  PARTIAL: "Partial",
  PENDING: "Pending",
};

export default function ArchiveReceiptCard({
  receipt,
  occupants,
  onViewPdf,
}: {
  receipt: Receipt;
  occupants: Occupant[];
  onViewPdf?: (billNo: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const state = getPaymentState(receipt);
  const grandTotal = getGrandTotal(receipt);
  const received = getAmountReceived(receipt);

  const presentOccupants = occupants.filter((o) => {
    const start = new Date(`${o.residentSince}T00:00:00`);
    const monthEnd = new Date(
      new Date(receipt.Date || 0).getFullYear(),
      new Date(receipt.Date || 0).getMonth() + 1,
      0
    );
    return !Number.isNaN(start.getTime()) && start <= monthEnd;
  });

  return (
    <Card className="rounded-2xl border shadow-sm overflow-hidden">
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-muted flex items-center justify-center">
              <Archive className="h-4 w-4 text-muted-foreground" />
            </div>
            <div>
              <span className="font-semibold">{receipt.Month}</span>
              <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                <span>{receipt.Bill}</span>
                <span>&middot;</span>
                <span>{receipt.Date}</span>
              </div>
            </div>
          </div>
          <Badge variant="outline" className={cn("shrink-0", statusStyles[isSettled(receipt) ? "PAID" : state])}>
            {isSettled(receipt) ? "Settled" : statusLabels[state]}
          </Badge>
        </div>

        <div className="flex items-center gap-4 text-sm mt-3 mb-1">
          <span className="text-muted-foreground">
            Total: <span className="font-semibold text-foreground">{formatCurrency(grandTotal)}</span>
          </span>
          <span className="text-muted-foreground">
            Received: <span className="font-semibold text-foreground">{formatCurrency(received)}</span>
          </span>
        </div>

        <Collapsible open={open} onOpenChange={setOpen}>
          <CollapsibleTrigger asChild>
            <button className="w-full flex items-center justify-between mt-3 py-2 px-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors text-sm">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Users className="h-3.5 w-3.5" />
                <span>Occupants during this period</span>
                <Badge variant="outline" className="h-5 min-w-[1.25rem] px-1.5 text-[10px]">
                  {presentOccupants.length}
                </Badge>
              </div>
              {open ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 space-y-2">
            {presentOccupants.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-2">
                No occupant records for this period.
              </p>
            ) : (
              presentOccupants.map((o) => {
                const days = daysInMonth(o.residentSince, receipt.Month);
                const isActive = (o.status || "").toUpperCase() === "ACTIVE";
                return (
                  <div
                    key={o["Occupant UUID"] || o.occupantUuid}
                    className="flex items-center justify-between rounded-lg border p-3 bg-background"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={cn(
                          "h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0",
                          isActive
                            ? "bg-emerald-500/10 text-emerald-600"
                            : "bg-muted text-muted-foreground"
                        )}
                      >
                        {(o.name || "?").charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{o.name}</p>
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Badge
                            variant="outline"
                            className={cn(
                              "h-4 px-1 text-[9px] font-semibold",
                              isActive
                                ? "bg-emerald-500/10 text-emerald-600"
                                : "bg-muted text-muted-foreground"
                            )}
                          >
                            {isActive ? "Active" : "Inactive"}
                          </Badge>
                          <span>Since {formatResidentSince(o.residentSince)}</span>
                        </div>
                      </div>
                    </div>
                    <div className="text-right shrink-0 ml-3">
                      <p className="text-xs text-muted-foreground">Days</p>
                      <p className="text-sm font-bold">{days}</p>
                    </div>
                  </div>
                );
              })
            )}
          </CollapsibleContent>
        </Collapsible>

        <div className="flex gap-2 mt-3 pt-3 border-t border-border/50">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => onViewPdf?.(receipt.Bill)}
          >
            <Eye className="h-3.5 w-3.5 mr-1.5" />
            View PDF
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => window.open(tenantApi.pdf.downloadUrl(receipt.Bill), "_blank")}
          >
            <Download className="h-3.5 w-3.5 mr-1.5" />
            Download
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
