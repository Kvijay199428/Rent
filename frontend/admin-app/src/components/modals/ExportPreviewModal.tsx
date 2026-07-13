import { useEffect, useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import {
    Loader2,
    Search,
    FileSpreadsheet,
    AlertCircle,
    FileText,
    FileArchive,
    User,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
    fetchExportPreview,
    exportCsv,
    exportZip,
    exportExcel,
    downloadBlob,
    type ExportPreviewResponse,
    type TenantProfile,
    type Receipt,
} from './ExportService';
import { toast } from 'sonner';

// ─── Types ─────────────────────────────────────────────────────────

type ExportTarget = {
    tenant: TenantProfile;
    receipts: Receipt[];
};

type ExportPreviewModalProps = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
};

// ─── Helpers ───────────────────────────────────────────────────────

function formatCurrency(value?: string | number) {
    const num = Number(value || 0);
    if (Number.isNaN(num)) return '₹0.00';
    return `₹${num.toFixed(2)}`;
}

function getStatusTone(status: string) {
    switch ((status || '').toUpperCase()) {
        case 'ACTIVE':
            return 'bg-green-50 text-green-700 border-green-200';
        case 'INACTIVE':
            return 'bg-slate-50 text-slate-700 border-slate-200';
        case 'ARCHIVED':
            return 'bg-red-50 text-red-700 border-red-200';
        default:
            return 'bg-amber-50 text-amber-700 border-amber-200';
    }
}

function getPaymentTone(status: string) {
    switch ((status || '').toUpperCase()) {
        case 'PAID':
            return 'bg-green-50 text-green-700 border-green-200';
        case 'ADVANCE':
            return 'bg-emerald-50 text-emerald-700 border-emerald-200';
        case 'PARTIAL':
            return 'bg-amber-50 text-amber-700 border-amber-200';
        default:
            return 'bg-red-50 text-red-700 border-red-200';
    }
}

// ─── Component ─────────────────────────────────────────────────────

export default function ExportPreviewModal({
    open,
    onOpenChange,
}: ExportPreviewModalProps) {
    const [query, setQuery] = useState('');
    const [selectedTenant, setSelectedTenant] = useState<ExportTarget | null>(null);
    const [selectedTenantIds, setSelectedTenantIds] = useState<Set<number>>(new Set());
    const [isLoading, setIsLoading] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [previewData, setPreviewData] = useState<ExportPreviewResponse | null>(null);

    // Load preview data when modal opens
    useEffect(() => {
        if (open && !previewData) {
            setIsLoading(true);
            fetchExportPreview()
                .then((data) => {
                    setPreviewData(data);
                })
                .catch((err) => {
                    toast.error(err.message || 'Failed to load export preview');
                    console.error('Export preview error:', err);
                })
                .finally(() => {
                    setIsLoading(false);
                });
        }
    }, [open, previewData]);

    // Build tenant + receipts list
    const allTenants = useMemo(() => {
        const list: ExportTarget[] = [];
        if (!previewData?.tenants) return list;

        const receiptsByTenant = new Map<string, Receipt[]>();
        for (const receipt of previewData.receipts || []) {
            const tenantName = receipt.Tenant;
            if (!receiptsByTenant.has(tenantName)) {
                receiptsByTenant.set(tenantName, []);
            }
            receiptsByTenant.get(tenantName)!.push(receipt);
        }

        for (const tenant of previewData.tenants) {
            list.push({
                tenant,
                receipts: receiptsByTenant.get(tenant.name) || [],
            });
        }
        return list;
    }, [previewData]);

    // Filtered tenants based on search
    const filteredTenants = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return allTenants;
        return allTenants.filter((t) => {
            const name = (t.tenant.name || '').toLowerCase();
            const id = String(t.tenant.id).toLowerCase();
            const phone = (t.tenant.phone || '').toLowerCase();
            const company = (t.tenant.company || '').toLowerCase();
            const room = (t.tenant.roomNumber || '').toLowerCase();
            return (
                name.includes(q) ||
                id.includes(q) ||
                phone.includes(q) ||
                company.includes(q) ||
                room.includes(q)
            );
        });
    }, [allTenants, query]);

    // Stats
    const stats = useMemo(() => {
        const total = allTenants.length;
        const selected = selectedTenantIds.size;
        const totalReceipts = allTenants.reduce((sum, t) => sum + t.receipts.length, 0);
        return { total, selected, totalReceipts };
    }, [allTenants, selectedTenantIds]);

    // Auto-select first tenant on open
    useEffect(() => {
        if (!selectedTenant && filteredTenants.length > 0 && open) {
            setSelectedTenant(filteredTenants[0]);
        }
    }, [selectedTenant, filteredTenants, open]);

    // Keep selected tenant in sync if filtered list changes
    useEffect(() => {
        if (selectedTenant) {
            const stillExists = filteredTenants.find(
                (t) => t.tenant.id === selectedTenant.tenant.id
            );
            if (!stillExists && filteredTenants.length > 0) {
                setSelectedTenant(filteredTenants[0]);
            }
        }
    }, [filteredTenants, selectedTenant]);

    const toggleTenant = (tenantId: number) => {
        setSelectedTenantIds((prev) => {
            const next = new Set(prev);
            if (next.has(tenantId)) {
                next.delete(tenantId);
            } else {
                next.add(tenantId);
            }
            return next;
        });
    };

    const toggleAll = () => {
        if (selectedTenantIds.size === filteredTenants.length && filteredTenants.length > 0) {
            setSelectedTenantIds(new Set());
        } else {
            const all = new Set(filteredTenants.map((t) => t.tenant.id));
            setSelectedTenantIds(all);
        }
    };

    const getSelectedIds = (): number[] | 'all' => {
        if (selectedTenantIds.size === 0) return 'all';
        return Array.from(selectedTenantIds);
    };

    const handleExport = async (format: 'csv' | 'xlsx' | 'zip') => {
        const ids = getSelectedIds();
        const isAll = ids === 'all';
        const count = isAll ? stats.total : (ids as number[]).length;

        if (!isAll && count === 0) {
            toast.error('Please select at least one tenant to export');
            return;
        }

        setIsExporting(true);
        try {
            let blob: Blob;
            let filename: string;
            const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, '');

            switch (format) {
                case 'csv':
                    blob = await exportCsv(ids);
                    filename = `receipts_export_${dateStr}.csv`;
                    break;
                case 'xlsx':
                    blob = await exportExcel('xlsx', ids);
                    filename = `Rent_Data_Export_${dateStr}.xlsx`;
                    break;
                case 'zip':
                    blob = await exportZip(ids);
                    filename = `tenant_data_${dateStr}.zip`;
                    break;
            }

            downloadBlob(blob, filename);

            toast.success(
                `Exported ${format.toUpperCase()} for ${count} tenant${count !== 1 ? 's' : ''}`
            );
        } catch (err: any) {
            toast.error(err.message || `${format.toUpperCase()} export failed`);
            console.error('Export error:', err);
        } finally {
            setIsExporting(false);
        }
    };

    const active = selectedTenant ? selectedTenant.tenant.id : -1;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-[95vw] xl:max-w-[1400px] h-[92vh] p-0 flex flex-col gap-0 overflow-hidden">
                {/* Header */}
                <DialogHeader className="px-6 pt-5 pb-3 shrink-0 border-b">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <FileSpreadsheet className="h-6 w-6 text-blue-500 shrink-0" />
                            <div>
                                <DialogTitle className="text-xl">Export Preview</DialogTitle>
                                <DialogDescription className="mt-1 text-sm">
                                    Select tenants and choose export format
                                </DialogDescription>
                            </div>
                        </div>
                        <div className="flex flex-wrap items-center justify-end gap-2">
                            <Badge className="bg-blue-100 text-blue-700 border-blue-200">
                                {stats.total} Tenant{stats.total !== 1 ? 's' : ''}
                            </Badge>
                            <Badge className="bg-purple-100 text-purple-700 border-purple-200">
                                {stats.totalReceipts} Receipt{stats.totalReceipts !== 1 ? 's' : ''}
                            </Badge>
                            <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">
                                {stats.selected} Selected
                            </Badge>
                        </div>
                    </div>
                </DialogHeader>

                {/* Split Pane Content */}
                <div className="flex-1 min-h-0 flex">
                    {/* LEFT PANE: Tenant List */}
                    <div className="w-[380px] lg:w-[420px] border-r bg-muted/30 flex flex-col shrink-0">
                        <div className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider shrink-0 border-b bg-muted/50 flex items-center justify-between">
                            <span>Tenants ({filteredTenants.length})</span>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 text-xs"
                                onClick={toggleAll}
                            >
                                {selectedTenantIds.size === filteredTenants.length && filteredTenants.length > 0
                                    ? 'Deselect All'
                                    : 'Select All'}
                            </Button>
                        </div>

                        <div className="shrink-0 border-b p-3 space-y-2">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    placeholder="Search name, ID, phone, company, room"
                                    className="pl-9"
                                />
                            </div>
                        </div>

                        <ScrollArea className="flex-1">
                            <div className="p-2 space-y-1.5">
                                {isLoading ? (
                                    <div className="flex items-center justify-center p-8">
                                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                                    </div>
                                ) : filteredTenants.length === 0 ? (
                                    <div className="text-sm text-muted-foreground p-3">
                                        No tenants found.
                                    </div>
                                ) : (
                                    filteredTenants.map((target) => {
                                        const tenant = target.tenant;
                                        const isSelected = selectedTenantIds.has(tenant.id);
                                        const isActive = active === tenant.id;
                                        const receiptCount = target.receipts.length;

                                        return (
                                            <div
                                                key={tenant.id}
                                                onClick={() => setSelectedTenant(target)}
                                                className={cn(
                                                    "group relative rounded-lg border p-3 cursor-pointer transition-all",
                                                    "hover:bg-accent hover:border-accent-foreground/20",
                                                    isActive && "bg-primary/10 border-primary/50 ring-1 ring-primary/30",
                                                    !isActive && "bg-card border-border"
                                                )}
                                            >
                                                <div className="flex items-start gap-2">
                                                    <div
                                                        className="pt-0.5 shrink-0"
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            toggleTenant(tenant.id);
                                                        }}
                                                    >
                                                        <Checkbox
                                                            checked={isSelected}
                                                            className="h-4 w-4"
                                                        />
                                                    </div>
                                                    <div className="min-w-0 flex-1">
                                                        <div className="flex items-start justify-between gap-2">
                                                            <div className="min-w-0 flex-1">
                                                                <div className="font-semibold text-sm truncate">
                                                                    {tenant.name || 'Unnamed Tenant'}
                                                                </div>
                                                                <div className="text-xs text-muted-foreground mt-0.5">
                                                                    ID: {tenant.id}
                                                                    {tenant.roomNumber && ` • Room ${tenant.roomNumber}`}
                                                                </div>
                                                            </div>
                                                            <Badge
                                                                className={cn(
                                                                    getStatusTone(tenant.status || 'Active'),
                                                                    "text-[10px] h-5 px-1.5 shrink-0"
                                                                )}
                                                            >
                                                                {(tenant.status || 'Active').toUpperCase()}
                                                            </Badge>
                                                        </div>

                                                        <div className="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                                                            <span>{receiptCount} receipt{receiptCount !== 1 ? 's' : ''}</span>
                                                            {tenant.phone && (
                                                                <span>• {tenant.phone}</span>
                                                            )}
                                                        </div>

                                                        <div className="mt-1 text-xs text-muted-foreground">
                                                            Rent {formatCurrency(tenant.rent)}
                                                            {tenant.water && ` • Water ${formatCurrency(tenant.water)}`}
                                                        </div>
                                                    </div>
                                                </div>

                                                {isActive && (
                                                    <div className="absolute left-0 top-3 bottom-3 w-0.5 bg-primary rounded-r-full" />
                                                )}
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </ScrollArea>
                    </div>

                    {/* RIGHT PANE: Receipts Table */}
                    <div className="flex-1 flex flex-col min-w-0 bg-background">
                        {selectedTenant ? (
                            <>
                                {/* Tenant Header */}
                                <div className="px-5 py-3 border-b bg-muted/20 shrink-0">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                                                <User className="h-5 w-5 text-primary" />
                                            </div>
                                            <div>
                                                <h3 className="font-semibold text-base">
                                                    {selectedTenant.tenant.name || 'Unnamed Tenant'}
                                                </h3>
                                                <p className="text-xs text-muted-foreground">
                                                    ID: {selectedTenant.tenant.id}
                                                    {selectedTenant.tenant.company && ` • ${selectedTenant.tenant.company}`}
                                                    {selectedTenant.tenant.phone && ` • ${selectedTenant.tenant.phone}`}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Badge
                                                className={cn(
                                                    getStatusTone(selectedTenant.tenant.status || 'Active'),
                                                    "text-[10px] h-5 px-1.5"
                                                )}
                                            >
                                                {(selectedTenant.tenant.status || 'Active').toUpperCase()}
                                            </Badge>
                                            <Badge variant="outline" className="text-[10px] h-5 px-1.5">
                                                {selectedTenant.receipts.length} Receipts
                                            </Badge>
                                        </div>
                                    </div>
                                </div>

                                {/* Receipts Table */}
                                <div className="flex-1 min-h-0 overflow-auto">
                                    {selectedTenant.receipts.length === 0 ? (
                                        <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                                            <AlertCircle className="h-10 w-10 mb-3 opacity-40" />
                                            <p className="text-sm">No receipts found for this tenant</p>
                                        </div>
                                    ) : (
                                        <div className="p-4">
                                            <Table>
                                                <TableHeader className="sticky top-0 bg-background z-10">
                                                    <TableRow>
                                                        <TableHead className="w-[100px]">Bill No</TableHead>
                                                        <TableHead>Month</TableHead>
                                                        <TableHead>Date</TableHead>
                                                        <TableHead className="text-right">Rent</TableHead>
                                                        <TableHead className="text-right">Electricity</TableHead>
                                                        <TableHead className="text-right">Water</TableHead>
                                                        <TableHead className="text-right">Total</TableHead>
                                                        <TableHead>Status</TableHead>
                                                        <TableHead>Payment</TableHead>
                                                    </TableRow>
                                                </TableHeader>
                                                <TableBody>
                                                    {selectedTenant.receipts.map((receipt, idx) => (
                                                        <TableRow key={`${receipt.Bill}-${idx}`}>
                                                            <TableCell className="font-medium">
                                                                {receipt.Bill}
                                                            </TableCell>
                                                            <TableCell>{receipt.Month}</TableCell>
                                                            <TableCell className="text-muted-foreground text-sm">
                                                                {receipt.Date}
                                                            </TableCell>
                                                            <TableCell className="text-right">
                                                                {formatCurrency(receipt.Rent)}
                                                            </TableCell>
                                                            <TableCell className="text-right">
                                                                {formatCurrency(receipt.Electricity)}
                                                            </TableCell>
                                                            <TableCell className="text-right">
                                                                {formatCurrency(receipt.Water)}
                                                            </TableCell>
                                                            <TableCell className="text-right font-medium">
                                                                {formatCurrency(receipt.Total)}
                                                            </TableCell>
                                                            <TableCell>
                                                                <Badge
                                                                    className={cn(
                                                                        getStatusTone(receipt.Status || 'ACTIVE'),
                                                                        "text-[10px] h-5 px-1.5"
                                                                    )}
                                                                >
                                                                    {(receipt.Status || 'ACTIVE').toUpperCase()}
                                                                </Badge>
                                                            </TableCell>
                                                            <TableCell>
                                                                <Badge
                                                                    className={cn(
                                                                        getPaymentTone(receipt.paymentStatus || 'PENDING'),
                                                                        "text-[10px] h-5 px-1.5"
                                                                    )}
                                                                >
                                                                    {(receipt.paymentStatus || 'PENDING').toUpperCase()}
                                                                </Badge>
                                                            </TableCell>
                                                        </TableRow>
                                                    ))}
                                                </TableBody>
                                            </Table>
                                        </div>
                                    )}
                                </div>
                            </>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                                <AlertCircle className="h-10 w-10 mb-3 opacity-40" />
                                <p className="text-sm">Select a tenant from the left panel to preview receipts</p>
                            </div>
                        )}
                    </div>
                </div>

                <Separator />

                {/* Footer with Export Buttons */}
                <div className="px-6 py-4 shrink-0 flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">
                        {stats.selected === 0
                            ? 'All tenants will be exported (no selection)'
                            : `${stats.selected} of ${stats.total} tenant${stats.total !== 1 ? 's' : ''} selected for export`}
                    </p>
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onOpenChange(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleExport('csv')}
                            disabled={isExporting}
                        >
                            {isExporting ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <FileText className="mr-2 h-4 w-4" />
                            )}
                            Export CSV
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleExport('xlsx')}
                            disabled={isExporting}
                        >
                            {isExporting ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <FileSpreadsheet className="mr-2 h-4 w-4" />
                            )}
                            Export XLSX
                        </Button>
                        <Button
                            size="sm"
                            onClick={() => handleExport('zip')}
                            disabled={isExporting}
                        >
                            {isExporting ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <FileArchive className="mr-2 h-4 w-4" />
                            )}
                            Export ZIP
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}