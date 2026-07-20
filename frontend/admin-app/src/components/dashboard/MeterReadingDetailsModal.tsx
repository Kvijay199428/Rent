import { useEffect, useMemo, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { api } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import type { Receipt, Tenant } from '@/types';
import { Loader2, Gauge, User, Zap } from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenantId: number | null;
  billNo?: string | null;
};

function parseMonthOrder(month: string) {
  const parsed = new Date(`01 ${month}`);
  return Number.isNaN(parsed.getTime()) ? 0 : parsed.getTime();
}

export default function MeterReadingDetailsModal({ open, onOpenChange, tenantId, billNo }: Props) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [receipts, setReceipts] = useState<Receipt[]>([]);

  useEffect(() => {
    const load = async () => {
      if (!open || !tenantId) return;

      try {
        setLoading(true);
        const [tenantData, receiptData] = await Promise.all([
          api.getTenant(tenantId),
          api.getTenantReceipts(tenantId),
        ]);

        const sortedReceipts = [...receiptData].sort(
          (a, b) => parseMonthOrder(a.Month) - parseMonthOrder(b.Month),
        );

        setTenant(tenantData);
        setReceipts(sortedReceipts);
      } catch {
        toast.error('Failed to load meter reading details');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [open, tenantId]);

  const chartData = useMemo(() => {
    return receipts.map((receipt) => ({
      label: receipt.Month,
      units: Number(receipt.Units || 0),
      current: Number(receipt.Current || 0),
      previous: Number(receipt.Previous || 0),
      amount: Number(receipt.Electricity || 0),
    }));
  }, [receipts]);

  const latestReceipt = receipts.length ? receipts[receipts.length - 1] : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[96vw] xl:max-w-[1450px] h-[92vh] p-0 overflow-hidden flex flex-col">
        <DialogHeader className="px-6 pt-5 pb-3 border-b shrink-0">
          <div className="flex items-center justify-between gap-4">
            <div>
              <DialogTitle className="text-xl">Last Meter Reading Details</DialogTitle>
              <DialogDescription>
                Tenant electricity history, monthly readings, and usage trend
              </DialogDescription>
            </div>
            {billNo ? (
              <Badge className="bg-amber-100 text-amber-700 border-amber-200">
                Triggered by {billNo}
              </Badge>
            ) : null}
          </div>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center flex-1">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : tenant ? (
          <div className="flex flex-1 min-h-0">
            {/* Left pane — tenant profile */}
            <aside className="w-[300px] border-r bg-muted/20 p-4 overflow-auto shrink-0">
              <Card>
                <CardContent className="p-4 space-y-4">
                  <div className="flex items-center gap-2 font-semibold">
                    <User className="h-4 w-4 text-primary" /> Tenant Profile
                  </div>

                  <div className="space-y-2 text-sm">
                    <div><span className="text-muted-foreground">Name:</span> {tenant.name}</div>
                    <div><span className="text-muted-foreground">Phone:</span> {tenant.phone || '-'}</div>
                    <div><span className="text-muted-foreground">Room:</span> {tenant.roomNumber || '-'}</div>
                    <div><span className="text-muted-foreground">Meter ID:</span> {tenant.meterId || '-'}</div>
                    <div><span className="text-muted-foreground">Elec. Rate:</span> ₹{Number(tenant.electricityRate || 0).toFixed(2)}/unit</div>
                    <div><span className="text-muted-foreground">Prev. Meter:</span> {Number(tenant.previousMeter || 0).toFixed(2)}</div>
                  </div>

                  {latestReceipt ? (
                    <div className="pt-2 border-t space-y-2 text-sm">
                      <div className="flex items-center gap-2 font-semibold">
                        <Gauge className="h-4 w-4 text-amber-500" /> Latest Reading
                      </div>
                      <div><span className="text-muted-foreground">Month:</span> {latestReceipt.Month}</div>
                      <div><span className="text-muted-foreground">Current:</span> {Number(latestReceipt.Current || 0).toFixed(2)}</div>
                      <div><span className="text-muted-foreground">Units:</span> {Number(latestReceipt.Units || 0).toFixed(2)}</div>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            </aside>

            {/* Right pane — table + chart */}
            <section className="flex-1 min-w-0 flex flex-col overflow-hidden">
              <div className="p-4 border-b shrink-0">
                <div className="flex items-center gap-2 font-semibold">
                  <Zap className="h-4 w-4 text-amber-500" /> Monthly Electricity Table
                </div>
              </div>

              <div className="flex-1 min-h-0 overflow-auto p-4 space-y-4">
                <Card>
                  <CardContent className="p-0">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Month</TableHead>
                          <TableHead>Previous</TableHead>
                          <TableHead>Current</TableHead>
                          <TableHead>Units</TableHead>
                          <TableHead>Rate</TableHead>
                          <TableHead>Electricity</TableHead>
                          <TableHead>Payment</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {receipts.map((receipt) => (
                          <TableRow key={receipt.Bill}>
                            <TableCell>{receipt.Month}</TableCell>
                            <TableCell>{Number(receipt.Previous || 0).toFixed(2)}</TableCell>
                            <TableCell>{Number(receipt.Current || 0).toFixed(2)}</TableCell>
                            <TableCell>{Number(receipt.Units || 0).toFixed(2)}</TableCell>
                            <TableCell>₹{Number(receipt.Rate || 0).toFixed(2)}</TableCell>
                            <TableCell>₹{Number(receipt.Electricity || 0).toFixed(2)}</TableCell>
                            <TableCell>
                              <Badge
                                className={
                                  String(receipt.paymentStatus).toUpperCase() === 'PAID'
                                    ? 'bg-green-100 text-green-700 border-green-200'
                                    : String(receipt.paymentStatus).toUpperCase() === 'PARTIAL'
                                      ? 'bg-amber-100 text-amber-700 border-amber-200'
                                      : 'bg-red-100 text-red-700 border-red-200'
                                }
                              >
                                {receipt.paymentStatus}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                        {receipts.length === 0 && (
                          <TableRow>
                            <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                              No receipts found for this tenant.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-4">
                    <div className="text-sm font-semibold mb-3">Monthly Electricity Usage Trend</div>
                    <ResponsiveContainer width="100%" height={280}>
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient id="tenantElecGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.35} />
                            <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.05} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip
                          contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)' }}
                          formatter={(value: number, name: string) => {
                            if (name === 'units') return [`${value} Units`, 'Consumed'];
                            if (name === 'amount') return [`₹${value}`, 'Charge'];
                            return [value, name];
                          }}
                        />
                        <Area
                          type="monotone"
                          dataKey="units"
                          stroke="#f59e0b"
                          fill="url(#tenantElecGrad)"
                          strokeWidth={2}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              </div>
            </section>
          </div>
        ) : (
          <div className="flex items-center justify-center flex-1 text-muted-foreground">
            No tenant selected for meter reading details
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
