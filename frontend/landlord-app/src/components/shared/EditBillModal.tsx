import { useState, useEffect, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { api } from '@/services/api';
import type { Receipt, Property, Tenant } from '@/types';
import { useToast } from '@/hooks/useToast';
import { useAuth } from '@/contexts/AuthContext';
import { BrandWave } from '@shared/loading/BrandWave';
import { FileText, AlertCircle, Zap, Building2, User, Phone, Building, MapPin } from 'lucide-react';

interface EditBillModalProps {
  billNo: string | null;
  tenantId: number | null;
  onClose: () => void;
  onSaved: () => void;
}

export default function EditBillModal({ billNo, tenantId, onClose, onSaved }: EditBillModalProps) {
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [properties, setProperties] = useState<Property[]>([]);
  const [months, setMonths] = useState<string[]>([]);
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Editable billing values (snapshot-driven, defaulting to the receipt's
  // stored snapshot so legacy receipts pre-date personal rate fields).
  const [propertyId, setPropertyId] = useState<string>('');
  const [rent, setRent] = useState(0);
  const [water, setWater] = useState(0);
  const [tankWater, setTankWater] = useState(0);
  const [maintenance, setMaintenance] = useState(0);
  const [maintenanceDesc, setMaintenanceDesc] = useState('');
  const [currentReading, setCurrentReading] = useState(0);
  const [elecRate, setElecRate] = useState(0);
  const [addPersons, setAddPersons] = useState(0);
  const [addPersonRate, setAddPersonRate] = useState(0);

  const toast = useToast();
  const { landlordUuid } = useAuth();
  const [dialogContainer, setDialogContainer] = useState<HTMLDivElement | null>(null);

  useEffect(() => {
    if (billNo && tenantId && landlordUuid) {
      setLoading(true);
      Promise.all([
        api.getReceipt(landlordUuid, tenantId, billNo),
        api.getProperties(landlordUuid).catch(() => []),
        api.getBillingMonths(landlordUuid),
        api.getTenant(landlordUuid, tenantId).catch(() => null),
      ])
        .then(([r, props, m, tenant]) => {
          setReceipt(r);
          setProperties(props);
          setMonths(m.months);
          setTenant(tenant);
          // Editable snapshot values come from the receipt record.
          setRent(r.Rent ?? 0);
          setWater(r.Water ?? 0);
          setTankWater(r.tankWater ?? 0);
          setMaintenance(r.MaintenanceCharge ?? 0);
          setMaintenanceDesc(r.MaintenanceDesc ?? '');
          setCurrentReading(r.Current ?? 0);
          setElecRate(r.Rate ?? 0);
          setAddPersons(r.Additional_Persons ?? 0);
          setAddPersonRate(r.additionalPersonRate ?? 0);
          // Property defaults to the receipt snapshot, else the tenant's
          // current property. Editing Property only affects this bill.
          const initialProp =
            r.propertyId != null
              ? String(r.propertyId)
              : tenant && tenant.propertyId != null
                ? String(tenant.propertyId)
                : '';
          setPropertyId(initialProp);
        })
        .catch(() => toast.error('Failed to load bill data'))
        .finally(() => setLoading(false));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [billNo, tenantId, landlordUuid]);

  const prevReading = receipt?.Previous ?? 0;
  const consumed = currentReading - prevReading;
  const electricity = consumed > 0 ? consumed * elecRate : 0;
  const additional = addPersons * addPersonRate;
  const currentTotal = rent + water + tankWater + maintenance + additional + electricity;
  const grandTotal = currentTotal + (receipt?.previousArrears ?? 0);

  const meterError =
    consumed < 0
      ? `Current Reading (${currentReading}) cannot be smaller than Previous Reading (${prevReading}).`
      : '';

  // Tenant info to display: prefer the live fetched tenant, fall back to the
  // snapshot stored on the receipt (in case the tenant fetch failed).
  const tenantInfo = tenant
    ? {
        name: tenant.name,
        phone: tenant.phone ?? '',
        company: tenant.company ?? '',
        address: tenant.address ?? '',
      }
    : {
        name: receipt?.Tenant ?? '',
        phone: receipt?.Tenant_Phone ?? '',
        company: receipt?.Tenant_Company ?? '',
        address: receipt?.Tenant_Address ?? '',
      };

  const breakdown = useMemo(
    () => [
      ['Rent', rent],
      ['Water', water],
      ['Tank Water', tankWater],
      ['Maintenance', maintenance],
      ['Additional', additional],
      ['Electricity', electricity],
    ],
    [rent, water, tankWater, maintenance, additional, electricity]
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!receipt) return;
    if (consumed < 0) {
      toast.error(meterError || 'Current reading cannot be less than previous reading');
      return;
    }

    setSaving(true);
    try {
      await api.updateBill(landlordUuid!, receipt.TenantId, receipt.Bill, {
        tenant: receipt.Tenant,
        month: receipt.Month,
        current_reading: currentReading,
        additional_persons: addPersons,
        tankWater: tankWater,
        MaintenanceCharge: maintenance,
        MaintenanceDesc: maintenanceDesc,
        previousArrears: receipt.previousArrears || 0,
        amountReceived: receipt.amountReceived ?? null,
        paymentStatus: receipt.paymentStatus || 'PENDING',
        rent: rent,
        water: water,
        electricityRate: elecRate,
        additionalPersonRate: addPersonRate,
        property_id: propertyId ? Number(propertyId) : null,
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
      <DialogContent ref={setDialogContainer} className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader className="pr-8">
          <DialogTitle className="flex items-center gap-2 min-w-0">
            <FileText className="h-5 w-5 text-primary shrink-0" />
            <span className="truncate">Edit Receipt</span>
            {receipt && (
              <span className="shrink-0 text-sm font-normal text-muted-foreground">
                #{receipt.Bill}
              </span>
            )}
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="py-8 text-center text-muted-foreground">
            <BrandWave stacked label="Loading bill…" />
          </div>
        ) : receipt ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Property + Tenant */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2 min-w-0">
                <Label className="flex items-center gap-1.5">
                  <Building2 className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  Property
                </Label>
                <Select value={propertyId} onValueChange={setPropertyId}>
                  <SelectTrigger className="w-full" size="sm">
                    <SelectValue placeholder="Select Property..." />
                  </SelectTrigger>
                  <SelectContent container={dialogContainer}>
                    {properties.map((p) => (
                      <SelectItem key={p.id} value={String(p.id)}>
                        <span className="truncate">
                          {p.property_name}
                          {p.address ? ` — ${p.address}` : ''}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Editable per-bill only; does not change the tenant’s property.
                </p>
              </div>
              <div className="space-y-2 min-w-0">
                <Label className="flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                  Tenant
                </Label>
                <div className="rounded-md border bg-muted px-3 py-2 text-sm">
                  <div className="truncate font-medium" title={tenantInfo.name}>
                    {tenantInfo.name || '—'}
                  </div>
                  {(tenantInfo.phone || tenantInfo.company) && (
                    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-muted-foreground">
                      {tenantInfo.phone && (
                        <span className="inline-flex items-center gap-1 truncate">
                          <Phone className="h-3 w-3 shrink-0" />
                          <span className="truncate">{tenantInfo.phone}</span>
                        </span>
                      )}
                      {tenantInfo.company && (
                        <span className="inline-flex items-center gap-1 truncate">
                          <Building className="h-3 w-3 shrink-0" />
                          <span className="truncate">{tenantInfo.company}</span>
                        </span>
                      )}
                    </div>
                  )}
                  {tenantInfo.address && (
                    <div className="mt-1 inline-flex items-center gap-1 text-muted-foreground">
                      <MapPin className="h-3 w-3 shrink-0" />
                      <span className="truncate">{tenantInfo.address}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Billing Month */}
            <div className="space-y-2">
              <Label>Billing Month</Label>
              <Select
                value={receipt.Month}
                onValueChange={(v) => setReceipt({ ...receipt, Month: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent container={dialogContainer}>
                  {months.map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Separator />

            {/* Fixed Charges */}
            <div>
              <h5 className="font-semibold text-muted-foreground mb-3 text-sm uppercase tracking-wider">
                Fixed Charges
              </h5>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-2">
                  <Label>Monthly Rent (₹)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={rent === 0 ? '' : rent}
                    onChange={(e) => setRent(parseFloat(e.target.value) || 0)}
                    className="border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Water Charge (₹)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={water === 0 ? '' : water}
                    onChange={(e) => setWater(parseFloat(e.target.value) || 0)}
                    className="border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Tank Water Charge (₹)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={tankWater === 0 ? '' : tankWater}
                    onChange={(e) => setTankWater(parseFloat(e.target.value) || 0)}
                    className="border-primary"
                  />
                </div>
              </div>
            </div>

            {/* Maintenance */}
            <div>
              <h5 className="font-semibold text-muted-foreground mb-3 text-sm uppercase tracking-wider">
                Maintenance &amp; Other Charges
              </h5>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-2">
                  <Label>Amount (₹)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={maintenance === 0 ? '' : maintenance}
                    onChange={(e) => setMaintenance(parseFloat(e.target.value) || 0)}
                    className="border-primary"
                  />
                </div>
                <div className="space-y-2 sm:col-span-2">
                  <Label>Description (Optional)</Label>
                  <Input
                    value={maintenanceDesc}
                    onChange={(e) => setMaintenanceDesc(e.target.value)}
                    placeholder="e.g. Building Maintenance"
                    disabled={maintenance <= 0}
                  />
                </div>
              </div>
            </div>

            {/* Electricity */}
            <div>
              <h5 className="font-semibold text-muted-foreground mb-3 text-sm uppercase tracking-wider">
                Electricity
              </h5>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-2">
                  <Label>Previous Reading</Label>
                  <Input type="number" value={prevReading || ''} disabled className="bg-muted" />
                </div>
                <div className="space-y-2">
                  <Label className="text-primary">Current Reading</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={currentReading === 0 ? '' : currentReading}
                    onChange={(e) => setCurrentReading(parseFloat(e.target.value) || 0)}
                    className="border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Electricity Rate (₹)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={elecRate === 0 ? '' : elecRate}
                    onChange={(e) => setElecRate(parseFloat(e.target.value) || 0)}
                    className="border-primary"
                  />
                </div>
              </div>
              <div className="mt-2 inline-flex items-center gap-2 px-3 py-1.5 rounded bg-primary/10 text-primary text-sm">
                <Zap className="h-4 w-4" />
                <span>
                  Consumed Units: <strong className="text-lg ml-1">{consumed.toFixed(1)}</strong>
                </span>
              </div>
              {meterError && (
                <div className="mt-2 p-2 rounded bg-red-50 text-red-600 text-sm flex items-center gap-2 dark:bg-red-900/20">
                  <AlertCircle className="h-4 w-4" /> {meterError}
                </div>
              )}
            </div>

            {/* Occupancy */}
            <div>
              <h5 className="font-semibold text-muted-foreground mb-3 text-sm uppercase tracking-wider">
                Occupancy
              </h5>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label className="text-primary">Additional Persons</Label>
                  <Input
                    type="number"
                    min={0}
                    value={addPersons === 0 ? '' : addPersons}
                    onChange={(e) => setAddPersons(parseInt(e.target.value) || 0)}
                    className="border-primary"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Rate per person (₹)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={addPersonRate === 0 ? '' : addPersonRate}
                    onChange={(e) => setAddPersonRate(parseFloat(e.target.value) || 0)}
                    className="border-primary"
                  />
                </div>
              </div>
            </div>

            {/* Previous Arrears (read-only) */}
            <div className="space-y-2">
              <Label>Previous Arrears (₹)</Label>
              <Input
                type="number"
                step="0.1"
                value={receipt.previousArrears || 0}
                disabled
                className="bg-muted"
              />
              <p className="text-xs text-muted-foreground">
                Auto-computed from unpaid balances; changes to payments cascade automatically.
              </p>
            </div>

            {/* Live Breakdown */}
            <div className="bg-gradient-to-br from-green-500 to-emerald-600 text-white rounded-xl p-5 shadow-lg">
              <h6 className="text-xs uppercase font-semibold text-white/70 tracking-wider mb-3">
                Live Breakdown
              </h6>
              <div className="space-y-1.5 text-sm">
                {breakdown.map(([label, val]) => (
                  <div key={label} className="flex justify-between">
                    <span className="text-white/70">{label}:</span>
                    <span className="font-semibold">₹{(val as number).toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <Separator className="my-3 bg-white/30" />
              <div className="flex justify-between text-sm">
                <span className="text-white/70">Current Bill Total:</span>
                <span className="font-semibold">
                  ₹{currentTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-yellow-200">Previous Arrears:</span>
                <span className="font-semibold">
                  ₹{(receipt.previousArrears ?? 0).toLocaleString('en-IN', {
                    minimumFractionDigits: 2,
                  })}
                </span>
              </div>
              <Separator className="my-3 bg-white/30" />
              <div className="flex justify-between items-center">
                <span className="text-lg font-bold">GRAND TOTAL</span>
                <span className="text-2xl font-bold">
                  ₹{grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
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
