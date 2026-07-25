import { Badge } from "@/components/ui/badge";
import type { PaymentState } from "@/types";

const styles: Record<PaymentState, string> = {
  PAID: "bg-emerald-500/10 text-emerald-600 hover:bg-emerald-500/20",
  PARTIAL: "bg-amber-500/10 text-amber-600 hover:bg-amber-500/20",
  PENDING: "bg-red-500/10 text-red-600 hover:bg-red-500/20",
  ADVANCE: "bg-cyan-500/10 text-cyan-600 hover:bg-cyan-500/20",
};

const labels: Record<PaymentState, string> = {
  PAID: "Paid",
  PARTIAL: "Partial",
  PENDING: "Pending",
  ADVANCE: "Advance",
};

export default function StatusBadge({ status }: { status: PaymentState }) {
  return (
    <Badge variant="outline" className={styles[status] ?? ""}>
      {labels[status] ?? status}
    </Badge>
  );
}
