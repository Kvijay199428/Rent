import { useState, useEffect } from 'react';
import QRCode from 'react-qr-code';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { api } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import type { Tenant } from '@/types';
import BillsModal, { type TenantBill } from '@/components/modals/BillsModal';
import OccupantsModal from '@/components/modals/OccupantsModal';
import { exportExcel, downloadBlob } from '@/components/modals/ExportService';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Users,
  Plus,
  Search,
  Pencil,
  Trash2,
  Receipt,
  Phone,
  Mail,
  Building,
  MapPin,
  Gauge,
  Download,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';

function formatDisplayDate(date = new Date()) {
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function buildQrPrintHtml({
  tenantName,
  roomNumber,
  pin,
  url,
}: {
  tenantName: string;
  roomNumber?: string;
  pin: string;
  url: string;
}) {
  const safeTenantName = escapeHtml(tenantName || 'Tenant');
  const safeRoom = escapeHtml(roomNumber || '-');
  const safePin = escapeHtml(pin || '----');
  const safeUrl = escapeHtml(url);
  const displayDate = formatDisplayDate();

  return `<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>${safeTenantName} - Portal QR</title>
    <style>
      @page {
        size: A4 portrait;
        margin: 0;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        padding: 0;
        background: #ffffff;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
        color: #111827;
      }

      .page {
        width: 210mm;
        height: 297mm;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 18mm;
      }

      .card {
        width: 100%;
        max-width: 128mm;
        border: 4px solid #222;
        border-radius: 24px;
        background: #fff;
        padding: 18mm 12mm 14mm;
        text-align: center;
      }

      .title {
        margin: 0;
        font-size: 18pt;
        line-height: 1.2;
        font-weight: 700;
        color: #6b7280;
      }

      .tenant {
        margin-top: 8px;
        font-size: 12pt;
        font-weight: 700;
        letter-spacing: 0.6px;
        color: #1f2937;
        text-transform: uppercase;
      }

      .qr-wrap {
        margin: 16px auto 12px;
        width: 360px;
        height: 360px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #fff;
        padding: 14px;
      }

      .instructions {
        margin: 10px auto 0;
        max-width: 300px;
        font-size: 11pt;
        line-height: 1.5;
        color: #374151;
      }

      .divider {
        margin: 18px auto 14px;
        width: 88%;
        border-top: 2px dashed #e5e7eb;
      }

      .room {
        font-size: 12pt;
        font-weight: 700;
        color: #6b7280;
        margin-bottom: 14px;
      }

      .pin-card {
        display: inline-block;
        min-width: 220px;
        padding: 12px 24px;
        border: 2px solid #222;
        border-radius: 10px;
        background: #fff;
      }

      .pin-label {
        font-size: 10pt;
        font-weight: 600;
        color: #6b7280;
        margin-bottom: 6px;
      }

      .pin-value {
        font-size: 20pt;
        font-weight: 800;
        letter-spacing: 3px;
        color: #1e3a8a;
      }

      .footer {
        margin-top: 18px;
        font-size: 10pt;
        line-height: 1.5;
        color: #6b7280;
      }

      #qr {
        line-height: 0;
      }
    </style>
  </head>
  <body>
    <div class="page">
      <div class="card">
        <h1 class="title">Scan to View Bills</h1>
        <div class="tenant">${safeTenantName}</div>

        <div class="qr-wrap">
          <div id="qr"></div>
        </div>

        <div class="instructions">
          Point your smartphone camera here to view your rent profile, latest bills, and payment status.
        </div>

        <div class="divider"></div>

        <div class="room">Room: ${safeRoom}</div>

        <div class="pin-card">
          <div class="pin-label">Tenant PIN</div>
          <div class="pin-value">${safePin}</div>
        </div>

        <div class="footer">
          <div>Generated: ${displayDate}</div>
          <div>VEGA RENT SYSTEM</div>
        </div>
      </div>
    </div>

    <script src="https://cdn.rawgit.com/davidshimjs/qrcodejs/gh-pages/qrcode.min.js"></script>
    <script>
      new QRCode(document.getElementById("qr"), {
        text: "${safeUrl}",
        width: 340,
        height: 340,
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
      });
    </script>
  </body>
</html>`;
}

function printHtmlInSameWindow(html: string) {
  const iframe = document.createElement('iframe');
  iframe.style.position = 'fixed';
  iframe.style.right = '0';
  iframe.style.bottom = '0';
  iframe.style.width = '0';
  iframe.style.height = '0';
  iframe.style.border = '0';
  iframe.setAttribute('aria-hidden', 'true');

  document.body.appendChild(iframe);

  const frameDoc = iframe.contentWindow?.document;
  if (!frameDoc) {
    document.body.removeChild(iframe);
    throw new Error('Unable to open print frame');
  }

  frameDoc.open();
  frameDoc.write(html);
  frameDoc.close();

  const cleanup = () => {
    setTimeout(() => {
      if (document.body.contains(iframe)) {
        document.body.removeChild(iframe);
      }
    }, 1000);
  };

  iframe.onload = () => {
    setTimeout(() => {
      iframe.contentWindow?.focus();
      iframe.contentWindow?.print();
      cleanup();
    }, 500);
  };
}

export default function Tenants() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);

  const [qrTenant, setQrTenant] = useState<Tenant | null>(null);
  const [qrPin, setQrPin] = useState('1234');
  const [qrPinLoading, setQrPinLoading] = useState(false);
  const [showQrPinEditor, setShowQrPinEditor] = useState(false);
  const [newQrPin, setNewQrPin] = useState('');
  const [savingQrPin, setSavingQrPin] = useState(false);
  const [occupantsTenant, setOccupantsTenant] = useState<Tenant | null>(null);

  const [billsTenant, setBillsTenant] = useState<Tenant | null>(null);
  const [tenantBills, setTenantBills] = useState<TenantBill[]>([]);
  const [billsLoading, setBillsLoading] = useState(false);
  const [selectedBill, setSelectedBill] = useState<TenantBill | null>(null);

  const toast = useToast();


  const handleExportTenant = async (tenantId: number, name: string, format: 'xlsx' | 'csv' | 'zip') => {
    try {
      toast.info(`Exporting ${name} as ${format.toUpperCase()}...`);
      const blob = await exportExcel(format, [tenantId]);
      downloadBlob(blob, `Tenant_${name}_${format.toUpperCase()}.${format}`);
      toast.success('Export successful');
    } catch (e: any) {
      toast.error(`Export failed: ${e.message}`);
    }
  };

  const qrPinMissing = !qrPinLoading && (!qrPin || qrPin === '----');

  const handleSaveQrPin = async () => {
    if (!qrTenant || !qrTenant.id || newQrPin.length !== 4) return;

    try {
      setSavingQrPin(true);
      await api.CHANGETENANTPIN(qrTenant.id, { pin: newQrPin, logout_all: true });
      setQrPin(newQrPin);
      setNewQrPin('');
      setShowQrPinEditor(false);
      toast.success('Tenant PIN updated');
    } catch (e: any) {
      toast.error(e?.message || 'Failed to update tenant PIN');
    } finally {
      setSavingQrPin(false);
    }
  };

  const handleShowQr = async (tenant: Tenant) => {
    if (!tenant.id) return;
    setQrTenant(tenant);
    setQrPin('----');
    setQrPinLoading(true);
    setShowQrPinEditor(false);
    setNewQrPin('');

    try {
      const res = await api.revealTenantPin(tenant.id);
      setQrPin(res.pin || '----');
    } catch {
      setQrPin('----');
    } finally {
      setQrPinLoading(false);
    }
  };

  const handleOpenOccupants = (tenant: Tenant) => {
    setOccupantsTenant(tenant);
  };

  const loadTenantBills = async (tenant: Tenant) => {
    try {
      setBillsLoading(true);
      const receipts = await api.getTenantReceipts(tenant.id as number);
      const active = (receipts ?? [])
        .filter((r: any) => r.Status !== 'ARCHIVED')
        .map((r: any) => ({
          Bill: r.Bill,
          Month: r.Month,
          Status: r.Status,
          PaymentStatus: r.paymentStatus,
          Total: r.Total,
          PreviousArrears: r.previousArrears,
          AmountReceived: r.amountReceived,
        }));
      setTenantBills(active);
      setSelectedBill(null);
      setBillsTenant(tenant);
    } catch {
      toast.error('Failed to load tenant bills');
      setTenantBills([]);
      setSelectedBill(null);
    } finally {
      setBillsLoading(false);
    }
  };

  const loadTenants = async () => {
    try {
      setLoading(true);
      const data = await api.getTenants();

      for (const t of data) {
        try {
          const receipts = await api.getTenantReceipts(t.id as number);
          const active = receipts.filter((r: any) => r.Status !== 'ARCHIVED');
          if (active.length > 0) {
            const latest = active[0];
            const grandTotal = Number(latest.Total || 0) + Number(latest.previousArrears || 0);
            const amtRecv = latest.amountReceived != null ? Number(latest.amountReceived) : grandTotal;
            t.arrears = grandTotal - amtRecv;
          } else {
            t.arrears = 0;
          }
        } catch {
          t.arrears = 0;
        }
      }

      setTenants(data);
    } catch {
      toast.error('Failed to load tenants');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

  const filtered = tenants.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      (t.company || '').toLowerCase().includes(search.toLowerCase()) ||
      (t.phone || '').includes(search)
  );

  const handleDelete = async (tenant: Tenant, action: string) => {
    if (!tenant.id) return;
    try {
      await api.deleteTenant(tenant.id, action);
      toast.success(`Tenant ${action}d successfully`);
      loadTenants();
    } catch {
      toast.error(`Failed to ${action} tenant`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b">
        <h1 className="text-2xl font-bold">Tenants</h1>
        <div className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search tenants..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 w-64"
            />
          </div>

          <Dialog open={showAdd} onOpenChange={setShowAdd}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4 mr-1" /> Add Tenant
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Add New Tenant</DialogTitle>
              </DialogHeader>
              <TenantForm
                onSave={async (data) => {
                  try {
                    await api.addTenant(data as any);
                    toast.success('Tenant added');
                    setShowAdd(false);
                    loadTenants();
                  } catch {
                    toast.error('Failed to add tenant');
                  }
                }}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Tabs defaultValue="all">
        <TabsList>
          <TabsTrigger value="all">All ({tenants.length})</TabsTrigger>
          <TabsTrigger value="active">
            Active ({tenants.filter((t) => t.status === 'Active').length})
          </TabsTrigger>
          <TabsTrigger value="inactive">
            Inactive ({tenants.filter((t) => t.status === 'Inactive').length})
          </TabsTrigger>
        </TabsList>

        {['all', 'active', 'inactive'].map((tab) => (
          <TabsContent key={tab} value={tab}>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filtered
                .filter((t) => tab === 'all' || t.status.toLowerCase() === tab)
                .map((tenant) => (
                  <TenantCard
                    key={tenant.id}
                    tenant={tenant}
                    onEdit={() => setEditingTenant(tenant)}
                    onDelete={(action) => handleDelete(tenant, action)}
                    onShowQr={() => handleShowQr(tenant)}
                    onShowOccupants={() => handleOpenOccupants(tenant)}
                    onShowBills={() => loadTenantBills(tenant)}
                    onExport={(format) => tenant.id && handleExportTenant(tenant.id, tenant.name, format)}
                    onStatusChange={async (newStatus) => {
                      if (!tenant.id) return;
                      try {
                        await api.updateTenant(tenant.id, { ...tenant, status: newStatus });
                        loadTenants();
                      } catch {
                        toast.error('Failed to update status');
                      }
                    }}
                  />
                ))}
            </div>

            {filtered.filter((t) => tab === 'all' || t.status.toLowerCase() === tab).length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No tenants found.</p>
              </div>
            )}
          </TabsContent>
        ))}
      </Tabs>

      <Dialog open={!!editingTenant} onOpenChange={() => setEditingTenant(null)}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Tenant</DialogTitle>
          </DialogHeader>
          {editingTenant && (
            <TenantForm
              tenant={editingTenant}
              onSave={async (data) => {
                if (!editingTenant.id) return;
                try {
                  await api.updateTenant(editingTenant.id, { ...editingTenant, ...data });
                  toast.success('Tenant updated');
                  setEditingTenant(null);
                  loadTenants();
                } catch {
                  toast.error('Failed to update tenant');
                }
              }}
              onChangePin={async (pin) => {
                if (!editingTenant.id) return;
                try {
                  await api.CHANGETENANTPIN(editingTenant.id, { pin, logout_all: true });
                  toast.success('Tenant PIN changed');
                  loadTenants();
                } catch (e: any) {
                  toast.error(e?.message || 'Failed to change tenant PIN');
                }
              }}
            />
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={!!qrTenant} onOpenChange={() => {
        setQrTenant(null);
        setShowQrPinEditor(false);
        setNewQrPin('');
      }}>
        <DialogContent className="max-w-[420px] p-4">
          <DialogHeader className="pb-1">
            <DialogTitle className="text-base">{qrTenant?.name} QR</DialogTitle>
          </DialogHeader>

          {qrTenant?.viewToken && (
            <div className="flex justify-center">
              <div className="w-full max-w-[340px] rounded-[22px] border-[3px] border-neutral-900 bg-white px-5 py-5 text-center shadow-sm">
                <h3 className="text-[16px] font-bold tracking-tight text-gray-500">
                  Scan to View Bills
                </h3>

                <div className="mt-2 text-[16px] font-bold uppercase tracking-[0.04em] text-gray-800">
                  {qrTenant.name}
                </div>

                <div className="mt-4 flex justify-center bg-white p-2">
                  <QRCode
                    value={`${window.location.origin}/rent/t/${qrTenant.id}/${qrTenant.viewToken}`}
                    size={200}
                    level="H"
                  />
                </div>

                <div className="my-4 border-t border-dashed border-gray-200" />

                <div className="text-lg font-bold text-gray-500">
                  Room: {qrTenant.roomNumber || '-'}
                </div>

                {qrPinMissing && (
                  <div className="mt-4 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    Tenant PIN is not set. Use Change PIN to create one.
                  </div>
                )}

                <div className="mt-4">
                  {!showQrPinEditor ? (
                    <div className="flex flex-col items-center">
                      {!qrPinMissing && (
                        <div className="mx-auto inline-flex min-w-[200px] flex-col rounded-[10px] border-2 border-neutral-900 px-5 py-3">
                          <span className="text-xs font-semibold text-gray-500">Tenant PIN</span>
                          <span className="text-2xl font-extrabold tracking-[0.2em] text-blue-900">
                            {qrPinLoading ? '••••' : qrPin}
                          </span>
                        </div>
                      )}

                      <Button
                        type="button"
                        variant={qrPinMissing ? 'outline' : 'ghost'}
                        size="sm"
                        className={qrPinMissing ? 'mt-3 w-full' : 'mt-2 text-xs text-gray-500'}
                        onClick={() => setShowQrPinEditor(true)}
                      >
                        Change PIN
                      </Button>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-neutral-300 p-3 text-left mt-3">
                      <div className="space-y-2">
                        <Label className="text-xs font-medium">New 4-digit PIN</Label>
                        <Input
                          type="password"
                          inputMode="numeric"
                          maxLength={4}
                          value={newQrPin}
                          onChange={(e) =>
                            setNewQrPin(e.target.value.replace(/\D/g, '').slice(0, 4))
                          }
                          placeholder="Enter PIN"
                          className="text-center tracking-[0.25em]"
                        />
                      </div>

                      <div className="mt-3 flex gap-2">
                        <Button
                          type="button"
                          size="sm"
                          className="flex-1"
                          disabled={newQrPin.length !== 4 || savingQrPin}
                          onClick={handleSaveQrPin}
                        >
                          {savingQrPin ? 'Saving...' : 'Save PIN'}
                        </Button>

                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          className="flex-1"
                          disabled={savingQrPin}
                          onClick={() => {
                            setShowQrPinEditor(false);
                            setNewQrPin('');
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-4 text-xs leading-5 text-gray-500">
                  <div>Generated: {formatDisplayDate()}</div>
                  <div>VEGA RENT SYSTEM</div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <OccupantsModal
        tenant={occupantsTenant}
        open={Boolean(occupantsTenant)}
        onOpenChange={(open) => {
          if (!open) setOccupantsTenant(null);
        }}
      />

      <BillsModal
        open={!!billsTenant}
        onOpenChange={(open) => {
          if (!open) {
            setBillsTenant(null);
            setTenantBills([]);
            setSelectedBill(null);
          }
        }}
        tenantId={billsTenant?.id ?? null}
        tenantname={billsTenant?.name}
        bills={tenantBills}
        loading={billsLoading}
        selectedBill={selectedBill}
        onSelectBill={setSelectedBill}
      />
    </div>
  );
}

function TenantCard({
  tenant,
  onEdit,
  onDelete,
  onShowQr,
  onShowOccupants,
  onShowBills,
  onExport,
  onStatusChange,
}: {
  tenant: Tenant;
  onEdit: () => void;
  onDelete: (action: string) => void;
  onShowQr: () => void;
  onShowOccupants: () => void;
  onShowBills: () => void;
  onExport: (format: 'xlsx' | 'csv' | 'zip') => void;
  onStatusChange: (newStatus: string) => void;
}) {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-lg">
              {tenant.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h3 className="font-semibold">{tenant.name}</h3>
              {/* Inline status toggle */}
              <div className="flex items-center gap-1 mt-1">
                <button
                  title="Set Active"
                  onClick={(e) => { e.stopPropagation(); if (tenant.status !== 'Active') onStatusChange('Active'); }}
                  className={`flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-medium transition-colors ${
                    tenant.status === 'Active'
                      ? 'bg-green-100 text-green-700'
                      : 'text-muted-foreground hover:bg-green-50 hover:text-green-700'
                  }`}
                >
                  <CheckCircle size={11} /> Active
                </button>
                <button
                  title="Set Inactive"
                  onClick={(e) => { e.stopPropagation(); if (tenant.status !== 'Inactive') onStatusChange('Inactive'); }}
                  className={`flex items-center gap-0.5 rounded px-1.5 py-0.5 text-xs font-medium transition-colors ${
                    tenant.status === 'Inactive'
                      ? 'bg-slate-200 text-slate-700'
                      : 'text-muted-foreground hover:bg-slate-100'
                  }`}
                >
                  <XCircle size={11} /> Inactive
                </button>
              </div>
            </div>
          </div>
          <div className="flex gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onEdit} title="Edit">
              <Pencil size={14} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-red-500"
              onClick={() => onDelete(tenant.status === 'Active' ? 'archive' : 'hard')}
              title={tenant.status === 'Active' ? 'Archive' : 'Delete'}
            >
              <Trash2 size={14} />
            </Button>
          </div>
        </div>

        <div className="space-y-1.5 text-sm">
          {tenant.phone && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Phone size={14} /> {tenant.phone}
            </div>
          )}
          {tenant.email && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Mail size={14} /> {tenant.email}
            </div>
          )}
          {tenant.company && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Building size={14} /> {tenant.company}
            </div>
          )}
          {tenant.address && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <MapPin size={14} /> {tenant.address}
            </div>
          )}
          {tenant.roomNumber && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Receipt size={14} /> Room {tenant.roomNumber}
            </div>
          )}
          {tenant.meterId && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Gauge size={14} /> Meter: {tenant.meterId}
            </div>
          )}
        </div>

        <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t">
          <div className="text-center">
            <div className="text-xs text-muted-foreground">Rent</div>
            <div className="font-semibold text-sm">₹{tenant.rent}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground">Water</div>
            <div className="font-semibold text-sm">₹{tenant.water}</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground">Elec Rate</div>
            <div className="font-semibold text-sm">₹{tenant.electricityRate}</div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t">
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            disabled={!tenant.viewToken}
            onClick={() => tenant.viewToken && window.open(`/rent/t/${tenant.id}/${tenant.viewToken}`, '_blank')}
            title={!tenant.viewToken ? 'Portal token missing for this tenant' : 'Open public profile'}
          >
            Public Profile
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="w-full"
            disabled={!tenant.viewToken}
            onClick={onShowQr}
            title={!tenant.viewToken ? 'Portal token missing for this tenant' : 'Show QR'}
          >
            QR
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="w-full"
            disabled={!tenant.viewToken}
            onClick={async () => {
              if (!tenant.viewToken || !tenant.id) return;

              const url = `${window.location.origin}/rent/t/${tenant.id}/${tenant.viewToken}`;

              let pin = '----';
              try {
                const res = await api.revealTenantPin(tenant.id);
                pin = res.pin || '----';
              } catch (e) {
                console.error('Failed to fetch tenant PIN', e);
              }

              const htmlContent = buildQrPrintHtml({
                tenantName: tenant.name,
                roomNumber: tenant.roomNumber || '-',
                pin,
                url,
              });

              try {
                printHtmlInSameWindow(htmlContent);
              } catch (e) {
                console.error('Failed to print QR', e);
                toast.error('Failed to open print dialog');
              }
            }}
            title={!tenant.viewToken ? 'Portal token missing for this tenant' : 'Print QR'}
          >
            Print QR
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={onShowOccupants}
          >
            <Users className="mr-1 h-4 w-4" />
            Occupants
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={onShowBills}
          >
            Bills
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="w-full">
                <Download className="h-3.5 w-3.5 mr-1.5" /> Export
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => onExport('xlsx')}>Excel (.xlsx)</DropdownMenuItem>
              <DropdownMenuItem onClick={() => onExport('csv')}>CSV</DropdownMenuItem>
              <DropdownMenuItem onClick={() => onExport('zip')}>ZIP File</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {tenant.arrears !== 0 && (
          <div
            className={`mt-2 text-center text-sm font-medium py-1 rounded ${tenant.arrears > 0
              ? 'bg-red-50 text-red-600 dark:bg-red-900/20'
              : 'bg-green-50 text-green-600 dark:bg-green-900/20'
              }`}
          >
            {tenant.arrears > 0
              ? `Due: ₹${tenant.arrears.toFixed(2)}`
              : `Advance: ₹${Math.abs(tenant.arrears).toFixed(2)}`}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function TenantForm({
  tenant,
  onSave,
  onChangePin,
}: {
  tenant?: Tenant | null;
  onSave: (data: Record<string, unknown>) => void;
  onChangePin?: (pin: string) => Promise<void>;
}) {
  const [newPin, setNewPin] = useState('');
  const [changingPin, setChangingPin] = useState(false);

  const [form, setForm] = useState({
    name: tenant?.name || '',
    phone: tenant?.phone || '',
    email: tenant?.email || '',
    company: tenant?.company || '',
    address: tenant?.address || '',
    roomNumber: tenant?.roomNumber || '',
    meterId: tenant?.meterId || '',
    rent: tenant?.rent || 8000,
    water: tenant?.water || 500,
    electricityRate: tenant?.electricityRate || 15,
    additionalPersonCharge: tenant?.additionalPersonCharge || 1000,
    defaulttankWaterCharge: tenant?.defaulttankWaterCharge || 0,
    previousMeter: tenant?.previousMeter || 0,
    status: tenant?.status || 'Active',
    tenantPin: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(form);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label>Name *</Label>
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        </div>
        <div className="space-y-2">
          <Label>Phone</Label>
          <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label>Email</Label>
          <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div className="space-y-2">
          <Label>Company</Label>
          <Input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
        </div>
      </div>

      <div className="space-y-2">
        <Label>Address</Label>
        <Input value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div className="space-y-2">
          <Label>Room #</Label>
          <Input value={form.roomNumber} onChange={(e) => setForm({ ...form, roomNumber: e.target.value })} />
        </div>
        <div className="space-y-2">
          <Label>Meter ID</Label>
          <Input value={form.meterId} onChange={(e) => setForm({ ...form, meterId: e.target.value })} />
        </div>
        <div className="space-y-2">
          <Label>Status</Label>
          <Select
            value={form.status === "Inactive" ? "Inactive" : "Active"}
            onValueChange={(status: string) => setForm({ ...form, status })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Active">ACTIVE</SelectItem>
              <SelectItem value="Inactive">INACTIVE</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="border-t pt-4">
        <h4 className="font-semibold text-sm text-muted-foreground mb-3 uppercase tracking-wider">
          Billing Profile
        </h4>
        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-2">
            <Label>Rent (₹)</Label>
            <Input type="number" value={form.rent} onChange={(e) => setForm({ ...form, rent: parseFloat(e.target.value) || 0 })} />
          </div>
          <div className="space-y-2">
            <Label>Water (₹)</Label>
            <Input type="number" value={form.water} onChange={(e) => setForm({ ...form, water: parseFloat(e.target.value) || 0 })} />
          </div>
          <div className="space-y-2">
            <Label>Elec Rate</Label>
            <Input
              type="number"
              step="0.1"
              value={form.electricityRate}
              onChange={(e) => setForm({ ...form, electricityRate: parseFloat(e.target.value) || 0 })}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mt-3">
          <div className="space-y-2">
            <Label>Add Person (₹)</Label>
            <Input
              type="number"
              value={form.additionalPersonCharge}
              onChange={(e) => setForm({ ...form, additionalPersonCharge: parseFloat(e.target.value) || 0 })}
            />
          </div>
          <div className="space-y-2">
            <Label>Tank Water (₹)</Label>
            <Input
              type="number"
              step="0.1"
              value={form.defaulttankWaterCharge}
              onChange={(e) => setForm({ ...form, defaulttankWaterCharge: parseFloat(e.target.value) || 0 })}
            />
          </div>
          <div className="space-y-2">
            <Label>Prev Meter</Label>
            <Input
              type="number"
              step="0.1"
              value={form.previousMeter}
              onChange={(e) => setForm({ ...form, previousMeter: parseFloat(e.target.value) || 0 })}
            />
          </div>
        </div>
      </div>

      {!tenant && (
        <div className="space-y-2">
          <Label>Tenant PIN (4 digits) *</Label>
          <Input
            type="password"
            maxLength={4}
            pattern="\d{4}"
            value={form.tenantPin}
            onChange={(e) => setForm({ ...form, tenantPin: e.target.value })}
            placeholder="Required for tenant portal access"
            required={!tenant}
          />
        </div>
      )}

      {tenant && (
        <div className="border-t pt-4 space-y-3">
          <h4 className="font-semibold text-sm text-muted-foreground uppercase tracking-wider">
            Tenant Portal PIN
          </h4>

          <div className="grid grid-cols-[1fr_auto] gap-3 items-end">
            <div className="space-y-2">
              <Label>Change PIN</Label>
              <Input
                type="password"
                maxLength={4}
                pattern="\d{4}"
                value={newPin}
                onChange={(e) => setNewPin(e.target.value.replace(/\D/g, '').slice(0, 4))}
                placeholder="Enter new 4-digit PIN"
              />
            </div>

            <Button
              type="button"
              variant="outline"
              disabled={!onChangePin || newPin.length !== 4 || changingPin}
              onClick={async () => {
                if (!onChangePin || newPin.length !== 4) return;
                try {
                  setChangingPin(true);
                  await onChangePin(newPin);
                  setNewPin('');
                } finally {
                  setChangingPin(false);
                }
              }}
            >
              {changingPin ? 'Changing...' : 'Change PIN'}
            </Button>
          </div>
        </div>
      )}

      <Button type="submit" className="w-full">
        {tenant ? 'Update Tenant' : 'Add Tenant'}
      </Button>
    </form>
  );
}
