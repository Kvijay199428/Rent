import { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { api } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import type { Receipt } from '@/types';
import { Search, Archive, ChevronDown } from 'lucide-react';
import ReceiptRow from '@/components/shared/ReceiptRow';
import PDFPreviewModal from '@/components/shared/PDFPreviewModal';
import EditBillModal from '@/components/shared/EditBillModal';

interface GroupedReceipts {
  [year: string]: {
    [month: string]: Receipt[];
  };
}

export default function ArchivePage() {
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [previewBill, setPreviewBill] = useState<string | null>(null);
  const [editBill, setEditBill] = useState<string | null>(null);
  const toast = useToast();

  const loadReceipts = async () => {
    try {
      setLoading(true);
      const data = await api.getArchivedReceipts();
      setReceipts(data);
    } catch {
      toast.error('Failed to load archived receipts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReceipts();
  }, []);

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

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b">
        <h1 className="text-2xl font-bold">Archived Receipts</h1>
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search Tenant, Company, Amount..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase font-semibold">Archived Receipts</p>
                <p className="text-2xl font-bold mt-1">{receipts.length}</p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-primary-foreground">
                <Archive size={18} />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase font-semibold">Archived Years</p>
                <p className="text-2xl font-bold mt-1">{yearEntries.length}</p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-cyan-500 flex items-center justify-center text-white">
                <ChevronDown size={18} />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase font-semibold">Total Revenue</p>
                <p className="text-2xl font-bold mt-1">
                  ₹{receipts.reduce((s, r) => s + (r.Total || 0), 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-green-500 flex items-center justify-center text-white">
                <span className="text-lg font-bold">₹</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Content */}
      {yearEntries.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12 text-muted-foreground">
            <Archive className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <h3 className="text-lg font-semibold">No Archived Receipts</h3>
            <p className="text-sm mt-1">Receipts you archive will appear here.</p>
          </CardContent>
        </Card>
      ) : (
        yearEntries.map(([year, months]) => {
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
                    <span>{yearCount} Archived</span>
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
                        variant="archive"
                      />
                    ))}
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })
      )}

      <PDFPreviewModal billno={previewBill} onClose={() => setPreviewBill(null)} />
      <EditBillModal billno={editBill} onClose={() => setEditBill(null)} onSaved={loadReceipts} />
    </div>
  );
}
