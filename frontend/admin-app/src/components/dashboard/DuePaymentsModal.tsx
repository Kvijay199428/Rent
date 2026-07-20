import { useEffect, useMemo, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
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
import PDFPreviewModal from '@/components/shared/PDFPreviewModal';
import { AlertCircle, Eye, Loader2, Pencil, Search, User } from 'lucide-react';

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChanged: () => void;
};

type DueReceipt = Receipt & {
  grandTotal: number;
  received: number;
  due: number;
};

type DueGroup = {
  tenant: Tenant;
  receipts: DueReceipt[];
  totalDue: number;
};

function getReceiptAmounts(receipt: Receipt) {
  const total = Number(receipt.Total || 0) + Number(receipt.previousArrears || 0);
  const status = String(receipt.paymentStatus || 'PENDING').toUpperCase();
  const received =
    receipt.amountReceived !== null && receipt.amountReceived !== undefined
      ? Number(receipt.amountReceived)
      : status === 'PAID'
        ? total
        : 0;
  const due = Math.max(total - received, 0);
  return { total, received, due };
}

function PaymentUpdateDialog({
  open,
  onOpenChange,
  receipt,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  receipt: DueReceipt | null;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [paymentStatus, setPaymentStatus] = useState('PENDING');
  const [amountReceived, setAmountReceived] = useState('0');

  useEffect(() => {
    if (!receipt) return;
    setPaymentStatus(String(receipt.paymentStatus || 'PENDING').toUpperCase());
    setAmountReceived(String(Number(receipt.received || 0)));
  }, [receipt]);

  const handleSave = async () => {
    if (!receipt) return;

    let finalAmount: number | undefined = Number(amountReceived || 0);
    if (paymentStatus === 'PAID') finalAmount = receipt.grandTotal;
    if (paymentStatus === 'PENDING') finalAmount = 0;

    try {
      setSubmitting(true);
      await api.updatePaymentStatus(receipt.TenantId, receipt.Bill, {
        paymentStatus,
        amountReceived: finalAmount,
      });
      toast.success('Payment updated');
      onSaved();
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to update payment');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Update Payment</DialogTitle>
          <DialogDescription>
            {receipt ? `${receipt.Tenant} • ${receipt.Bill}` : 'Update receipt payment'}
          </DialogDescription>
        </DialogHeader>

        {receipt ? (
          <div className="space-y-4">
            <Card>
              <CardContent className="p-4 space-y-1 text-sm">
                <div className="flex justify-between"><span>Grand Total</span><span>₹{receipt.grandTotal.toFixed(2)}</span></div>
                <div className="flex justify-between"><span>Received</span><span>₹{receipt.received.toFixed(2)}</span></div>
                <div className="flex justify-between text-red-600 font-medium"><span>Due</span><span>₹{receipt.due.toFixed(2)}</span></div>
              </CardContent>
            </Card>

            <div className="space-y-2">
              <label className="text-sm font-medium">Payment Status</label>
              <select
                value={paymentStatus}
                onChange={(e) => setPaymentStatus(e.target.value)}
                className="w-full h-10 rounded-md border bg-background px-3 text-sm"
              >
                <option value="PENDING">PENDING</option>
                <option value="PARTIAL">PARTIAL</option>
                <option value="PAID">PAID</option>
                <option value="ADVANCE">ADVANCE</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Amount Received</label>
              <Input
                type="number"
                step="0.01"
                value={amountReceived}
                onChange={(e) => setAmountReceived(e.target.value)}
                disabled={paymentStatus === 'PAID' || paymentStatus === 'PENDING'}
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button onClick={handleSave} disabled={submitting}>
                {submitting ? 'Saving...' : 'Save'}
              </Button>
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

export default function DuePaymentsModal({ open, onOpenChange, onChanged }: Props) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState('');
  const [groups, setGroups] = useState<DueGroup[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<number | null>(null);
  const [previewBill, setPreviewBill] = useState<{ billNo: string; tenantId: number } | null>(null);
  const [editingReceipt, setEditingReceipt] = useState<DueReceipt | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [tenants, receipts] = await Promise.all([
        api.getTenants(),
        api.getActiveReceipts(),
      ]);

      const tenantMap = new Map<number, Tenant>(tenants.map((t) => [t.id, t]));
      const dueReceipts: DueReceipt[] = receipts
        .map((receipt) => {
          const amounts = getReceiptAmounts(receipt);
          return { ...receipt, grandTotal: amounts.total, received: amounts.received, due: amounts.due };
        })
        .filter((receipt) => {
          const status = String(receipt.paymentStatus || 'PENDING').toUpperCase();
          return ['PENDING', 'PARTIAL'].includes(status) && receipt.due > 0;
        });

      const grouped = new Map<number, DueGroup>();

      for (const receipt of dueReceipts) {
        const tenantId = Number(receipt.TenantId);
        const tenant =
          tenantMap.get(tenantId) ??
          ({
            id: tenantId,
            name: receipt.Tenant,
            status: 'Active',
            rent: 0,
            water: 0,
            defaulttankWaterCharge: 0,
            electricityRate: 0,
            previousMeter: 0,
            additionalPersonCharge: 0,
            securityDeposit: 0,
            arrears: 0,
          } as Tenant);

        if (!grouped.has(tenantId)) {
          grouped.set(tenantId, { tenant, receipts: [], totalDue: 0 });
        }

        const current = grouped.get(tenantId)!;
        current.receipts.push(receipt);
        current.totalDue += receipt.due;
      }

      const finalGroups = Array.from(grouped.values()).sort((a, b) => b.totalDue - a.totalDue);
      setGroups(finalGroups);
      setSelectedTenantId((prev) => prev ?? finalGroups[0]?.tenant.id ?? null);
    } catch {
      toast.error('Failed to load due payments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) loadData();
  }, [open]);

  const filteredGroups = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return groups;
    return groups.filter((group) => {
      const tenant = group.tenant;
      const tenantMatch =
        tenant.name.toLowerCase().includes(q) ||
        String(tenant.roomNumber || '').toLowerCase().includes(q) ||
        String(tenant.phone || '').toLowerCase().includes(q);
      const receiptMatch = group.receipts.some((receipt) =>
        [receipt.Bill, receipt.Month, receipt.paymentStatus].some((value) =>
          String(value || '').toLowerCase().includes(q),
        ),
      );
      return tenantMatch || receiptMatch;
    });
  }, [groups, query]);

  const selectedGroup =
    filteredGroups.find((group) => group.tenant.id === selectedTenantId) ?? filteredGroups[0] ?? null;

  useEffect(() => {
    if (!selectedGroup) return;
    if (selectedTenantId !== selectedGroup.tenant.id) {
      setSelectedTenantId(selectedGroup.tenant.id);
    }
  }, [selectedGroup, selectedTenantId]);

  const totalDueAmount = filteredGroups.reduce((sum, group) => sum + group.totalDue, 0);
  const totalDueReceipts = filteredGroups.reduce((sum, group) => sum + group.receipts.length, 0);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-[96vw] xl:max-w-[1450px] h-[92vh] p-0 overflow-hidden flex flex-col">
          <DialogHeader className="px-6 pt-5 pb-3 border-b shrink-0">
            <div className="flex items-center justify-between gap-4">
              <div>
                <DialogTitle className="text-xl">Due Payments</DialogTitle>
                <DialogDescription>Pending and partial receipts grouped by tenant</DialogDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge className="bg-red-100 text-red-700 border-red-200">₹{totalDueAmount.toFixed(2)} due</Badge>
                <Badge className="bg-amber-100 text-amber-700 border-amber-200">{filteredGroups.length} tenants</Badge>
                <Badge className="bg-blue-100 text-blue-700 border-blue-200">{totalDueReceipts} receipts</Badge>
              </div>
            </div>
          </DialogHeader>

          <div className="flex flex-1 min-h-0">
            {/* Left sidebar — tenant list */}
            <aside className="w-[340px] border-r bg-muted/20 flex flex-col shrink-0">
              <div className="p-4 border-b space-y-3">
                <div className="text-sm font-medium">Tenants with Dues</div>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search tenant, bill, month..."
                    className="pl-9"
                  />
                </div>
              </div>

              <ScrollArea className="flex-1">
                <div className="p-3 space-y-3">
                  {loading ? (
                    <div className="flex items-center justify-center py-10">
                      <Loader2 className="h-6 w-6 animate-spin text-primary" />
                    </div>
                  ) : filteredGroups.length === 0 ? (
                    <div className="text-sm text-muted-foreground p-3">No due receipts found.</div>
                  ) : (
                    filteredGroups.map((group) => {
                      const active = selectedGroup?.tenant.id === group.tenant.id;
                      return (
                        <button
                          key={group.tenant.id}
                          type="button"
                          onClick={() => setSelectedTenantId(group.tenant.id)}
                          className={`w-full rounded-xl border p-4 text-left transition ${
                            active
                              ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                              : 'border-border bg-background hover:bg-accent'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <div className="font-semibold text-sm truncate">{group.tenant.name}</div>
                              <div className="text-xs text-muted-foreground mt-1">
                                Room {group.tenant.roomNumber || '-'} • {group.tenant.phone || 'No phone'}
                              </div>
                            </div>
                            <Badge className="bg-red-100 text-red-700 border-red-200 shrink-0">
                              ₹{group.totalDue.toFixed(0)}
                            </Badge>
                          </div>
                          <div className="text-xs text-muted-foreground mt-3">
                            {group.receipts.length} due receipt{group.receipts.length !== 1 ? 's' : ''}
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </ScrollArea>
            </aside>

            {/* Right panel — receipts detail */}
            <section className="flex-1 min-w-0 flex flex-col overflow-hidden">
              {selectedGroup ? (
                <>
                  <div className="border-b p-5 bg-muted/20 shrink-0">
                    <div className="grid md:grid-cols-[320px,1fr] gap-4">
                      <Card>
                        <CardContent className="p-4 space-y-3">
                          <div className="flex items-center gap-2 font-semibold">
                            <User className="h-4 w-4 text-primary" /> Tenant Profile
                          </div>
                          <div className="text-sm space-y-1">
                            <div><span className="text-muted-foreground">Name:</span> {selectedGroup.tenant.name}</div>
                            <div><span className="text-muted-foreground">Phone:</span> {selectedGroup.tenant.phone || '-'}</div>
                            <div><span className="text-muted-foreground">Room:</span> {selectedGroup.tenant.roomNumber || '-'}</div>
                            <div><span className="text-muted-foreground">Company:</span> {selectedGroup.tenant.company || '-'}</div>
                            <div><span className="text-muted-foreground">Rent:</span> ₹{Number(selectedGroup.tenant.rent || 0).toFixed(2)}</div>
                          </div>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardContent className="p-4 space-y-2">
                          <div className="flex items-center gap-2 font-semibold">
                            <AlertCircle className="h-4 w-4 text-red-500" /> Due Summary
                          </div>
                          <div className="text-sm space-y-1">
                            <div className="flex justify-between"><span>Total due receipts</span><span>{selectedGroup.receipts.length}</span></div>
                            <div className="flex justify-between"><span>Total due amount</span><span>₹{selectedGroup.totalDue.toFixed(2)}</span></div>
                            <div className="flex justify-between"><span>Status filter</span><span className="text-muted-foreground">PENDING + PARTIAL</span></div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </div>

                  <div className="flex-1 min-h-0 overflow-auto p-4">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Bill</TableHead>
                          <TableHead>Month</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Grand Total</TableHead>
                          <TableHead>Received</TableHead>
                          <TableHead>Due</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedGroup.receipts.map((receipt) => (
                          <TableRow key={receipt.Bill}>
                            <TableCell className="font-mono text-xs">{receipt.Bill}</TableCell>
                            <TableCell>{receipt.Month}</TableCell>
                            <TableCell>
                              <Badge
                                className={
                                  String(receipt.paymentStatus).toUpperCase() === 'PARTIAL'
                                    ? 'bg-amber-100 text-amber-700 border-amber-200'
                                    : 'bg-red-100 text-red-700 border-red-200'
                                }
                              >
                                {receipt.paymentStatus}
                              </Badge>
                            </TableCell>
                            <TableCell>₹{receipt.grandTotal.toFixed(2)}</TableCell>
                            <TableCell>₹{receipt.received.toFixed(2)}</TableCell>
                            <TableCell className="text-red-600 font-medium">₹{receipt.due.toFixed(2)}</TableCell>
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => setPreviewBill({ billNo: receipt.Bill, tenantId: receipt.TenantId })}
                                >
                                  <Eye className="h-4 w-4 mr-2" /> Preview
                                </Button>
                                <Button
                                  size="sm"
                                  onClick={() => setEditingReceipt(receipt)}
                                >
                                  <Pencil className="h-4 w-4 mr-2" /> Update Payment
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-muted-foreground">
                  Select a tenant to inspect due receipts
                </div>
              )}
            </section>
          </div>
        </DialogContent>
      </Dialog>

      <PDFPreviewModal
        billNo={previewBill?.billNo ?? null}
        tenantId={previewBill?.tenantId ?? null}
        onClose={() => setPreviewBill(null)}
      />

      <PaymentUpdateDialog
        open={!!editingReceipt}
        onOpenChange={(value) => { if (!value) setEditingReceipt(null); }}
        receipt={editingReceipt}
        onSaved={async () => {
          await loadData();
          onChanged();
          setEditingReceipt(null);
        }}
      />
    </>
  );
}
