import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { api } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import type { Tenant, Receipt } from '@/types';
import { Search, Archive as ArchiveIcon, Loader2 } from 'lucide-react';
import { ArchiveTenantCard } from '@/components/archive/ArchiveTenantCard';
import PDFPreviewModal from '@/components/shared/PDFPreviewModal';
import EditBillModal from '@/components/shared/EditBillModal';
import ReceiptRow from '@/components/shared/ReceiptRow';

export default function ARCHIVEPAGE() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [previewBill, setPreviewBill] = useState<{ billNo: string; tenantId: number } | null>(null);
  const [editBill, setEditBill] = useState<{ billNo: string; tenantId: number } | null>(null);
  const toast = useToast();

  const loadArchive = async () => {
    try {
      setLoading(true);
      const data = await api.getArchiveData();
      setTenants(Array.isArray(data.tenants) ? data.tenants : []);
      setReceipts(Array.isArray(data.receipts) ? data.receipts : []);
    } catch {
      toast.error('Failed to load archive data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadArchive();
  }, []);

  // Group receipts strictly by TenantId — never by Tenant name
  const receiptsByTenantId = useMemo(() => {
    const map = new Map<number, Receipt[]>();
    for (const receipt of receipts) {
      const tid = Number(receipt.TenantId || 0);
      if (!tid) continue;
      const list = map.get(tid) ?? [];
      list.push(receipt);
      map.set(tid, list);
    }
    return map;
  }, [receipts]);

  // Archived tenant cards — each gets only receipts with matching TenantId
  const tenantCards = useMemo(() => {
    return tenants.map((tenant) => ({
      tenant,
      receipts: receiptsByTenantId.get(Number(tenant.id)) ?? [],
    }));
  }, [tenants, receiptsByTenantId]);

  // Orphan archived bills: bill is ARCHIVED but its tenant is still active (not in archived tenant list)
  const archivedTenantIds = useMemo(() => new Set(tenants.map((t) => Number(t.id))), [tenants]);
  const orphanBills = useMemo(() => {
    return receipts.filter((r) => {
      const tid = Number(r.TenantId || 0);
      return tid > 0 && !archivedTenantIds.has(tid);
    });
  }, [receipts, archivedTenantIds]);

  // Search filter across all receipts (name, bill, month)
  const filteredCards = useMemo(() => {
    if (!search.trim()) return tenantCards;
    const s = search.toLowerCase();
    return tenantCards
      .map(({ tenant, receipts }) => ({
        tenant,
        receipts: receipts.filter(
          (r) =>
            r.Tenant?.toLowerCase().includes(s) ||
            r.Bill?.toLowerCase().includes(s) ||
            r.Month?.toLowerCase().includes(s)
        ),
      }))
      .filter(
        ({ tenant, receipts: rs }) =>
          tenant.name?.toLowerCase().includes(s) ||
          String(tenant.id).includes(s) ||
          rs.length > 0
      );
  }, [tenantCards, search]);

  const filteredOrphans = useMemo(() => {
    if (!search.trim()) return orphanBills;
    const s = search.toLowerCase();
    return orphanBills.filter(
      (r) =>
        r.Tenant?.toLowerCase().includes(s) ||
        r.Bill?.toLowerCase().includes(s) ||
        r.Month?.toLowerCase().includes(s)
    );
  }, [orphanBills, search]);

  const totalArchived = tenantCards.reduce((s, c) => s + c.receipts.length, 0) + orphanBills.length;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <ArchiveIcon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Archive</h1>
            <p className="text-sm text-muted-foreground">
              Archived tenants and their receipts, grouped by tenant ID.
            </p>
          </div>
        </div>
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search tenant, bill, month..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground uppercase font-semibold">Archived Tenants</p>
            <p className="text-2xl font-bold mt-1">{tenants.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground uppercase font-semibold">Archived Receipts</p>
            <p className="text-2xl font-bold mt-1">{totalArchived}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground uppercase font-semibold">Bill-Only Archived</p>
            <p className="text-2xl font-bold mt-1">{orphanBills.length}</p>
          </CardContent>
        </Card>
      </div>

      {/* Empty state */}
      {filteredCards.length === 0 && filteredOrphans.length === 0 && (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">
            <ArchiveIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <h3 className="text-lg font-semibold">No Archived Data</h3>
            <p className="text-sm mt-1">
              {search ? 'No results match your search.' : 'Archived tenants and receipts will appear here.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Archived tenant cards — receipts grouped strictly by TenantId */}
      {filteredCards.map(({ tenant, receipts: tenantReceipts }) => (
        <ArchiveTenantCard
          key={tenant.id}
          tenant={tenant}
          receipts={tenantReceipts}
          onRefresh={loadArchive}
          onPreview={setPreviewBill}
          onEdit={setEditBill}
          onPermanentDelete={() => loadArchive()}
        />
      ))}

      {/* Orphan archived bills (bill-level archive, tenant still active) */}
      {filteredOrphans.length > 0 && (
        <Card className="overflow-hidden">
          <div className="px-4 py-3 border-b bg-muted/40">
            <h2 className="text-base font-semibold">Archived Bills (Active Tenants)</h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              These bills were individually archived while their tenant remains active.
            </p>
          </div>
          <CardContent className="p-0">
            {filteredOrphans.map((r) => (
              <ReceiptRow
                key={`${r.TenantId}-${r.Bill}`}
                receipt={r}
                onAction={loadArchive}
                onPreview={setPreviewBill}
                onEdit={setEditBill}
                variant="archive"
              />
            ))}
          </CardContent>
        </Card>
      )}

      <PDFPreviewModal
        billNo={previewBill?.billNo || null}
        tenantId={previewBill?.tenantId || null}
        onClose={() => setPreviewBill(null)}
      />
      <EditBillModal
        billNo={editBill?.billNo || null}
        tenantId={editBill?.tenantId || null}
        onClose={() => setEditBill(null)}
        onSaved={loadArchive}
      />
    </div>
  );
}
