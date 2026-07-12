import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import { Separator } from '@/components/ui/separator';
import { api } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import type { Tenant } from '@/types';
import { CheckCircle, FileText, Download, Clock, AlertCircle, Zap } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export default function Billing() {
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [months, setMonths] = useState<string[]>([]);
  const [currentMonth, setCurrentMonth] = useState('');
  const [loading, setLoading] = useState(true);

  // Form state
  const [selectedTenantId, setSelectedTenantId] = useState('');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [rent, setRent] = useState(0);
  const [water, setWater] = useState(0);
  const [tankWater, setTankWater] = useState(0);
  const [maintenance, setMaintenance] = useState(0);
  const [maintenanceDesc, setMaintenanceDesc] = useState('');
  const [prevReading, setPrevReading] = useState(0);
  const [currentReading, setCurrentReading] = useState<number | ''>('');
  const [elecRate, setElecRate] = useState(0);
  const [addPersons, setAddPersons] = useState(0);
  const [addPersonRate, setAddPersonRate] = useState(0);
  const [calculatedArrears, setCalculatedArrears] = useState(0);
  const [nextBillNo, setNextBillNo] = useState('');
  const [meterError, setMeterError] = useState('');

  // Result
  const [showSuccess, setShowSuccess] = useState(false);
  const [generatedBill, setGeneratedBill] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const toast = useToast();

  useEffect(() => {
    Promise.all([api.getTenants(), api.getBillingMonths()])
      .then(([t, m]) => {
        setTenants(t.filter((x: Tenant) => x.status === 'Active'));
        setMonths(m.months);
        setCurrentMonth(m.currentMonth);
        setSelectedMonth(m.currentMonth);
      })
      .catch(() => toast.error('Failed to load data'))
      .finally(() => setLoading(false));
  }, []);

  const handleTenantChange = useCallback(async (tenantId: string) => {
    setSelectedTenantId(tenantId);
    const tenant = tenants.find((t) => String(t.id) === tenantId);
    if (!tenant) return;

    try {
      const [tRes, recRes] = await Promise.all([
        api.getTenant(tenant.id),
        api.getTenantReceipts(tenant.name),
      ]);

      setRent(tRes.rent || 0);
      setWater(tRes.water || 0);
      setElecRate(tRes.electricity_rate || 0);
      setAddPersonRate(tRes.additional_person_charge || 0);
      setTankWater(tRes.default_tank_water_charge || 0);

      const receipts = recRes;
      let previousReading = 0;
      let maxSeq = 0;
      let arrears = 0;

      if (receipts.length > 0) {
        previousReading = Number(receipts[0].Current || 0);
        receipts.forEach((r) => {
          const parts = r.Bill.split('-');
          const seq = parts.length > 1 ? parseInt(parts[parts.length - 1]) : parseInt(r.Bill);
          if (!isNaN(seq)) maxSeq = Math.max(maxSeq, seq);
        });

        const last = receipts[0];
        const lastTotal = parseFloat(String(last.Total)) || 0;
        const lastPrevArr = parseFloat(String(last.Previous_Arrears)) || 0;
        const grandTotal = lastTotal + lastPrevArr;
        const lastRecv = last.Amount_Received !== null && last.Amount_Received !== undefined
          ? parseFloat(String(last.Amount_Received))
          : grandTotal;
        if (!isNaN(lastRecv)) {
          arrears = grandTotal - lastRecv;
        }
      } else {
        previousReading = Number(tRes.previous_meter || 0);
      }

      setPrevReading(previousReading);
      setCalculatedArrears(arrears);
      setNextBillNo(`T${tenant.id}-${String(maxSeq + 1).padStart(3, '0')}`);
      setCurrentReading('');
      setAddPersons(0);
      setMaintenance(0);
      setMaintenanceDesc('');
    } catch {
      toast.error('Failed to load tenant billing profile');
    }
  }, [tenants, toast]);

  const currentVal = typeof currentReading === 'number' ? currentReading : 0;
  const consumed = currentVal - prevReading;
  const electricity = consumed > 0 ? consumed * elecRate : 0;
  const additional = addPersons * addPersonRate;
  const currentTotal = rent + water + tankWater + maintenance + additional + electricity;
  const grandTotal = currentTotal + calculatedArrears;

  useEffect(() => {
    if (consumed < 0 && currentReading !== '') {
      setMeterError(`Current Reading (${currentVal}) cannot be smaller than Previous Reading (${prevReading}).`);
    } else {
      setMeterError('');
    }
  }, [consumed, currentVal, prevReading, currentReading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTenantId || !selectedMonth || currentVal < prevReading) {
      toast.error('Please fill all required fields correctly');
      return;
    }

    const tenant = tenants.find((t) => String(t.id) === selectedTenantId);
    if (!tenant) return;

    setSubmitting(true);
    try {
      const res = await api.createBill({
        tenant: tenant.name,
        month: selectedMonth,
        current_reading: currentVal,
        additional_persons: addPersons,
        tank_water: tankWater,
        maintenance_charge: maintenance,
        maintenance_desc: maintenanceDesc,
        previous_arrears: calculatedArrears,
        amount_received: null,
        payment_status: 'PENDING',
      });

      setGeneratedBill(res.data.Bill);
      setShowSuccess(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create receipt';
      if (msg.includes('already exists')) {
        toast.error('Bill already exists for this month');
      } else {
        toast.error(msg);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setSelectedTenantId('');
    setSelectedMonth(currentMonth);
    setRent(0);
    setWater(0);
    setTankWater(0);
    setMaintenance(0);
    setMaintenanceDesc('');
    setPrevReading(0);
    setCurrentReading('');
    setElecRate(0);
    setAddPersons(0);
    setAddPersonRate(0);
    setCalculatedArrears(0);
    setNextBillNo('');
    setMeterError('');
    setShowSuccess(false);
    setGeneratedBill(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <Card>
        <CardHeader className="bg-primary text-primary-foreground rounded-t-lg">
          <CardTitle className="flex items-center gap-2 text-lg">
            <FileText className="h-5 w-5" />
            Generate New Receipt
            {nextBillNo && (
              <span className="ml-2 px-2 py-0.5 rounded bg-white/20 text-sm font-mono">{nextBillNo}</span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Tenant */}
            <div className="space-y-2">
              <Label>Tenant Name</Label>
              <Select value={selectedTenantId} onValueChange={handleTenantChange}>
                <SelectTrigger>
                  <SelectValue placeholder="Select Tenant..." />
                </SelectTrigger>
                <SelectContent>
                  {tenants.map((t) => (
                    <SelectItem key={t.id} value={String(t.id)}>
                      {t.name} {t.room_number ? `(Room ${t.room_number})` : ''}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Billing Month */}
            <div className="space-y-2">
              <Label>Billing Month</Label>
              <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {months.map((m) => (
                    <SelectItem key={m} value={m}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Separator />

            {/* Fixed Charges */}
            <div>
              <h5 className="font-semibold text-muted-foreground mb-3 text-sm uppercase tracking-wider">Fixed Charges</h5>
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-2">
                  <Label>Monthly Rent (₹)</Label>
                  <Input type="number" value={rent || ''} disabled className="bg-muted" />
                </div>
                <div className="space-y-2">
                  <Label>Water Charge (₹)</Label>
                  <Input type="number" value={water || ''} disabled className="bg-muted" />
                </div>
                <div className="space-y-2">
                  <Label>Tank Water Charge (₹)</Label>
                  <Input type="number" step="0.1" value={tankWater || ''} onChange={(e) => setTankWater(parseFloat(e.target.value) || 0)} />
                </div>
              </div>
            </div>

            {/* Maintenance */}
            <div>
              <h5 className="font-semibold text-muted-foreground mb-3 text-sm uppercase tracking-wider">Maintenance & Other Charges</h5>
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-2">
                  <Label>Amount (₹)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={maintenance || ''}
                    onChange={(e) => setMaintenance(parseFloat(e.target.value) || 0)}
                    className="border-cyan-400"
                  />
                </div>
                <div className="space-y-2 col-span-2">
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
              <h5 className="font-semibold text-muted-foreground mb-3 text-sm uppercase tracking-wider">Electricity</h5>
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-2">
                  <Label>Previous Reading</Label>
                  <Input type="number" value={prevReading || ''} disabled className="bg-muted" />
                </div>
                <div className="space-y-2">
                  <Label className="text-primary">Current Reading</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={currentReading}
                    onChange={(e) => setCurrentReading(e.target.value === '' ? '' : parseFloat(e.target.value))}
                    className="border-primary"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Electricity Rate</Label>
                  <Input type="text" value={`₹${elecRate.toFixed(2)}`} disabled className="bg-muted" />
                </div>
              </div>
              <div className="mt-2 inline-flex items-center gap-2 px-3 py-1.5 rounded bg-primary/10 text-primary text-sm">
                <Zap className="h-4 w-4" />
                <span>Consumed Units: <strong className="text-lg ml-1">{consumed.toFixed(1)}</strong></span>
              </div>
              {meterError && (
                <div className="mt-2 p-2 rounded bg-red-50 text-red-600 text-sm flex items-center gap-2 dark:bg-red-900/20">
                  <AlertCircle className="h-4 w-4" /> {meterError}
                </div>
              )}
            </div>

            {/* Occupancy */}
            <div>
              <h5 className="font-semibold text-muted-foreground mb-3 text-sm uppercase tracking-wider">Occupancy</h5>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label className="text-primary">Additional Persons</Label>
                  <Input type="number" min={0} value={addPersons || ''} onChange={(e) => setAddPersons(parseInt(e.target.value) || 0)} className="border-primary" />
                </div>
                <div className="space-y-2">
                  <Label>Rate per person (₹)</Label>
                  <Input type="text" value={`₹${addPersonRate.toFixed(2)}`} disabled className="bg-muted" />
                </div>
              </div>
            </div>

            {/* Live Breakdown */}
            <div className="bg-gradient-to-br from-green-500 to-emerald-600 text-white rounded-xl p-5 shadow-lg">
              <h6 className="text-xs uppercase font-semibold text-white/70 tracking-wider mb-3">Live Breakdown</h6>
              <div className="space-y-1.5 text-sm">
                {[
                  ['Rent', rent],
                  ['Water', water],
                  ['Tank Water', tankWater],
                  ['Maintenance', maintenance],
                  ['Additional', additional],
                  ['Electricity', electricity],
                ].map(([label, val]) => (
                  <div key={label} className="flex justify-between">
                    <span className="text-white/70">{label}:</span>
                    <span className="font-semibold">₹{(val as number).toFixed(2)}</span>
                  </div>
                ))}
              </div>
              <Separator className="my-3 bg-white/30" />
              <div className="flex justify-between text-sm">
                <span className="text-white/70">Current Bill Total:</span>
                <span className="font-semibold">₹{currentTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className={calculatedArrears < 0 ? 'text-yellow-200' : 'text-yellow-200'}>
                  {calculatedArrears < 0 ? 'Previous Advance:' : 'Previous Arrears:'}
                </span>
                <span className="font-semibold">₹{Math.abs(calculatedArrears).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
              <Separator className="my-3 bg-white/30" />
              <div className="flex justify-between items-center">
                <span className="text-lg font-bold">GRAND TOTAL</span>
                <span className="text-2xl font-bold">₹{grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
            </div>

            <Button
              type="submit"
              className="w-full py-6 text-lg font-bold rounded-full shadow-lg"
              disabled={submitting || !!meterError || !selectedTenantId}
            >
              <CheckCircle className="h-5 w-5 mr-2" />
              {submitting ? 'Generating...' : 'Generate Receipt'}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Success Dialog */}
      <Dialog open={showSuccess} onOpenChange={setShowSuccess}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-500">
              <CheckCircle className="h-6 w-6" /> Receipt Generated
            </DialogTitle>
          </DialogHeader>
          <div className="text-center py-4">
            <p className="text-3xl font-bold text-green-600 dark:text-green-400">
              ₹{grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </p>
            <p className="text-muted-foreground mt-1">Receipt #{generatedBill}</p>
          </div>
          <div className="space-y-2">
            <Button variant="outline" className="w-full justify-start" onClick={() => generatedBill && window.open(api.getPDFViewUrl(generatedBill), '_blank')}>
              <FileText className="h-4 w-4 mr-2 text-primary" /> Preview Receipt
            </Button>
            <Button variant="outline" className="w-full justify-start" onClick={() => {
              if (!generatedBill) return;
              const a = document.createElement('a');
              a.href = api.getPDFDownloadUrl(generatedBill);
              a.download = `Receipt_${generatedBill}.pdf`;
              a.click();
            }}>
              <Download className="h-4 w-4 mr-2" /> Download PDF
            </Button>
            <Button variant="outline" className="w-full justify-start" onClick={() => navigate('/history')}>
              <Clock className="h-4 w-4 mr-2" /> Receipt History
            </Button>
          </div>
          <Button onClick={resetForm} className="w-full mt-2">
            Generate Another
          </Button>
        </DialogContent>
      </Dialog>
    </div>
  );
}
