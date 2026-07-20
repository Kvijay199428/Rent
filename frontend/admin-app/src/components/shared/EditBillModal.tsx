import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { api } from '@/services/api';
import type { Tenant, Receipt } from '@/types';
import { useToast } from '@/hooks/useToast';

interface EditBillModalProps {
  billNo: string | null;
  tenantId: number | null;
  onClose: () => void;
  onSaved: () => void;
}

export default function EditBillModal({ billNo, tenantId, onClose, onSaved }: EditBillModalProps) {
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [months, setMonths] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (billNo && tenantId) {
      setLoading(true);
      Promise.all([
        api.getReceipt(tenantId, billNo),
        api.getTenants(),
        api.getBillingMonths(),
      ])
        .then(([r, t, m]) => {
          setReceipt(r);
          setTenants(t.filter((x: Tenant) => x.status === 'Active'));
          setMonths(m.months);
        })
        .catch(() => toast.error('Failed to load bill data'))
        .finally(() => setLoading(false));
    }
  }, [billNo]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!receipt) return;

    setSaving(true);
    try {
      await api.updateBill(receipt.TenantId, receipt.Bill, {
        tenant: receipt.Tenant,
        month: receipt.Month,
        current_reading: receipt.Current,
        additional_persons: receipt.Additional_Persons || 0,
        tankWater: receipt.tankWater || 0,
        MaintenanceCharge: receipt.MaintenanceCharge || 0,
        MaintenanceDesc: receipt.MaintenanceDesc || '',
        previousArrears: receipt.previousArrears || 0,
        amountReceived: receipt.amountReceived || null,
        paymentStatus: receipt.paymentStatus || 'PENDING',
      });
      toast.success('Receipt updated successfully');
      onSaved();
      onClose();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to update receipt';
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={!!billNo} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>✏️</span> Edit Receipt
            {receipt && (
              <span className="text-sm font-normal text-muted-foreground">
                #{receipt.Bill}
              </span>
            )}
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="py-8 text-center text-muted-foreground">Loading...</div>
        ) : receipt ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Tenant</Label>
                <Select
                  value={receipt.Tenant}
                  onValueChange={(v) => setReceipt({ ...receipt, Tenant: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {tenants.map((t) => (
                      <SelectItem key={t.id} value={t.name}>
                        {t.name} {t.roomNumber ? `(Room ${t.roomNumber})` : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Billing Month</Label>
                <Select
                  value={receipt.Month}
                  onValueChange={(v) => setReceipt({ ...receipt, Month: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {months.map((m) => (
                      <SelectItem key={m} value={m}>
                        {m}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Current Reading</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={receipt.Current}
                  onChange={(e) => setReceipt({ ...receipt, Current: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label>Previous Reading</Label>
                <Input type="number" value={receipt.Previous} disabled className="bg-muted" />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Tank Water (₹)</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={receipt.tankWater || 0}
                  onChange={(e) => setReceipt({ ...receipt, tankWater: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label>Maintenance (₹)</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={receipt.MaintenanceCharge || 0}
                  onChange={(e) => setReceipt({ ...receipt, MaintenanceCharge: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <Label>Previous Arrears (₹)</Label>
                <Input
                  type="number"
                  step="0.1"
                  value={receipt.previousArrears || 0}
                  onChange={(e) => setReceipt({ ...receipt, previousArrears: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Maintenance Description</Label>
              <Input
                value={receipt.MaintenanceDesc || ''}
                onChange={(e) => setReceipt({ ...receipt, MaintenanceDesc: e.target.value })}
                placeholder="e.g. Building Maintenance"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </form>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
