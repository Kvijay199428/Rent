import { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { api } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import type { Receipt } from '@/types';
import { Search, Receipt as ReceiptIcon, ChevronDown } from 'lucide-react';
import ReceiptRow from '@/components/shared/ReceiptRow';
import PDFPreviewModal from '@/components/shared/PDFPreviewModal';
import EditBillModal from '@/components/shared/EditBillModal';

interface GroupedReceipts {
  [year: string]: {
    [month: string]: Receipt[];
  };
}

export default function History() {
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [previewBill, setPreviewBill] = useState<string | null>(null);
  const [editBill, setEditBill] = useState<string | null>(null);
  const [searchParams] = useSearchParams();
  const toast = useToast();

  const q = searchParams.get('q');

  const loadReceipts = async () => {
    try {
      setLoading(true);
      const data = await api.getActiveReceipts();
      setReceipts(data);
    } catch {
      toast.error('Failed to load receipts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReceipts();
  }, []);

  useEffect(() => {
    if (q) setSearch(q);
  }, [q]);

  const filteredReceipts = useMemo(() => {
    if (!search.trim()) return receipts;
    const s = search.toLowerCase();
    return receipts.filter(
      (r) =>
        r.Tenant.toLowerCase().includes(s) ||
        r.Bill.toLowerCase().includes(s) ||
        r.Month.toLowerCase().includes(s)
    );
  }, [receipts, search]);

  const grouped = useMemo(() => {
    const g: GroupedReceipts = {};
    filteredReceipts.forEach((r) => {
      const parts = r.Month.split(' ');
      const month = parts[0] || 'Unknown';
      const year = parts[1] || 'Unknown';
      if (!g[year]) g[year] = {};
      if (!g[year][month]) g[year][month] = [];
      g[year][month].push(r);
    });
    return g;
  }, [filteredReceipts]);

  const yearEntries = Object.entries(grouped).sort((a, b) => Number(b[0]) - Number(a[0]));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b">
        <h1 className="text-2xl font-bold">Receipt History</h1>
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search Tenant, Bill, Amount..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Content */}
      {yearEntries.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">
            <ReceiptIcon className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <h3 className="text-lg font-semibold">No Receipts Found</h3>
            <p className="text-sm mt-1">Receipts you generate will appear here.</p>
          </CardContent>
        </Card>
      ) : (
        yearEntries.map(([year, months]) => {
          const yearTotal = Object.values(months).flat().reduce((s, r) => s + (r.Total || 0), 0);
          const yearCount = Object.values(months).flat().length;

          return (
            <Card key={year} className="overflow-hidden">
              <CardHeader className="py-3 px-4 bg-muted/50 cursor-pointer">
                <CardTitle className="text-base flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-primary">📅</span>
                    <span>{year}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground font-normal">
                    <span>{yearCount} Bills</span>
                    <span>₹{yearTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    <ChevronDown className="h-4 w-4" />
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {Object.entries(months).map(([month, monthReceipts]) => (
                  <div key={month}>
                    <div className="px-4 py-2 bg-accent/30 border-b text-sm font-semibold text-muted-foreground flex items-center gap-2">
                      <ChevronDown className="h-3 w-3" />
                      {month}
                    </div>
                    {monthReceipts.map((r) => (
                      <ReceiptRow
                        key={r.Bill}
                        receipt={r}
                        onAction={loadReceipts}
                        onPreview={setPreviewBill}
                        onEdit={setEditBill}
                        variant="history"
                      />
                    ))}
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })
      )}

      <PDFPreviewModal billNo={previewBill} onClose={() => setPreviewBill(null)} />
      <EditBillModal billNo={editBill} onClose={() => setEditBill(null)} onSaved={loadReceipts} />
    </div>
  );
}
