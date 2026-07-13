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
import { Loader2, Search, FileSpreadsheet, AlertCircle, Upload, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { importExecute, type PreviewResponse } from './importService';
import { toast } from 'sonner';

// ─── Types ─────────────────────────────────────────────────────────

export type ImportProfile = {
    tenantId: string;
    tenantName: string;
    Phone: string;
    Email: string;
    Company: string;
    Address: string;
    Room: string;
    meterId: string;
    PIN: string;
    Rent: string;
    Water: string;
    electricityRate: string;
    additionalPersonRate: string;
    tankWater: string;
    Status: string;
};

export type ImportReceipt = {
    BillNo: string;
    tenantId: string;
    Month: string;
    Date: string;
    Previous: string;
    Current: string;
    Units: string;
    Rent: string;
    Water: string;
    Electricity: string;
    Additional: string;
    tankWater: string;
    Maintenance: string;
    Arrears: string;
    amountReceived: string;
    Total: string;
    paymentStatus: string;
    receiptStatus: string;
};

export type ImportTarget = {
    file: string;
    tenantId: string;
    profile: ImportProfile;
    receipts: ImportReceipt[];
};

type ImportPreviewModalProps = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    previewData: PreviewResponse | null;
    files: File[];
    onImportSuccess: () => void;
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

function makeTargetKey(file: string, tenantId: string) {
    return `${file}::${tenantId}`;
}

// ─── Component ─────────────────────────────────────────────────────

export default function ImportPreviewModal({
    open,
    onOpenChange,
    previewData,
    files,
    onImportSuccess,
}: ImportPreviewModalProps) {
    const [query, setQuery] = useState('');
    const [selectedTenant, setSelectedTenant] = useState<ImportTarget | null>(null);
    const [selectedTargets, setSelectedTargets] = useState<Set<string>>(new Set());
    const [isExecuting, setIsExecuting] = useState(false);

    type TenantStatus = "Active" | "Inactive" | "Archived";
    const [statusDialogOpen, setStatusDialogOpen] = useState(false);
    const [targetStatuses, setTargetStatuses] = useState<Record<string, TenantStatus>>({});

    // Flatten preview data into a list of tenants
    const allTenants = useMemo(() => {
        const list: ImportTarget[] = [];
        if (!previewData?.files) return list;
        for (const [file, tenants] of Object.entries(previewData.files)) {
            for (const [tenantId, entry] of Object.entries(tenants)) {
                list.push({
                    file,
                    tenantId,
                    profile: entry.profile,
                    receipts: entry.receipts,
                });
            }
        }
        return list;
    }, [previewData]);

    useEffect(() => {
        const next: Record<string, TenantStatus> = {};
        allTenants.forEach((tenant) => {
            const key = makeTargetKey(tenant.file, tenant.tenantId);
            const importedStatus = tenant.profile.Status?.trim().toUpperCase();

            next[key] = importedStatus === "ARCHIVED"
                ? "Active"
                : (tenant.profile.Status?.trim().replace(/^./, c => c.toUpperCase()) as TenantStatus || "Active");
        });
        setTargetStatuses(next);
    }, [allTenants]);

    // Filtered tenants based on search
    const filteredTenants = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return allTenants;
        return allTenants.filter((t) => {
            const name = (t.profile.tenantName || '').toLowerCase();
            const tid = (t.profile.tenantId || '').toLowerCase();
            const phone = (t.profile.Phone || '').toLowerCase();
            const company = (t.profile.Company || '').toLowerCase();
            return name.includes(q) || tid.includes(q) || phone.includes(q) || company.includes(q);
        });
    }, [allTenants, query]);

    // Stats
    const stats = useMemo(() => {
        const total = allTenants.length;
        const selected = selectedTargets.size;
        const totalReceipts = allTenants.reduce((sum, t) => sum + t.receipts.length, 0);
        return { total, selected, totalReceipts };
    }, [allTenants, selectedTargets]);

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
                (t) => t.file === selectedTenant.file && t.tenantId === selectedTenant.tenantId
            );
            if (!stillExists && filteredTenants.length > 0) {
                setSelectedTenant(filteredTenants[0]);
            }
        }
    }, [filteredTenants, selectedTenant]);

    const toggleTarget = (targetKey: string) => {
        setSelectedTargets((prev) => {
            const next = new Set(prev);
            if (next.has(targetKey)) {
                next.delete(targetKey);
            } else {
                next.add(targetKey);
            }
            return next;
        });
    };

    const toggleAll = () => {
        if (selectedTargets.size === filteredTenants.length) {
            setSelectedTargets(new Set());
        } else {
            const all = new Set(filteredTenants.map((t) => makeTargetKey(t.file, t.tenantId)));
            setSelectedTargets(all);
        }
    };

    const handleConfirm = () => {
        if (selectedTargets.size === 0) {
            toast.error("Please select at least one tenant to import");
            return;
        }

        const containsArchivedSource = Array.from(selectedTargets).some((key) => {
            const tenant = allTenants.find(
                (item) => makeTargetKey(item.file, item.tenantId) === key
            );
            return tenant?.profile.Status?.trim().toUpperCase() === "ARCHIVED";
        });

        if (containsArchivedSource) {
            setStatusDialogOpen(true);
            return;
        }

        executeImport();
    };

    const executeImport = async () => {
        setIsExecuting(true);
        try {
            const targets = Array.from(selectedTargets);
            const selectedStatusMap = Object.fromEntries(
                targets.map((target) => [target, targetStatuses[target] || "Active"])
            );

            const result = await importExecute(files, targets, selectedStatusMap);
            toast.success(result.message || "Import completed successfully");
            onImportSuccess();
            onOpenChange(false);
        } catch (err: any) {
            toast.error(err?.message || "Import failed");
            console.error("Import execute error:", err);
        } finally {
            setIsExecuting(false);
            setStatusDialogOpen(false);
        }
    };

    const active = selectedTenant
        ? makeTargetKey(selectedTenant.file, selectedTenant.tenantId)
        : '';

    return (
        <>
        <Dialog open={open} onOpenChange={onOpenChange}>
            {/* Match PreviewDialog / BillsModal sizing pattern exactly */}
            <DialogContent className="max-w-[95vw] xl:max-w-[1400px] h-[92vh] p-0 flex flex-col gap-0 overflow-hidden">
                {/* Header — Match BillsModal header styling */}
                <DialogHeader className="px-6 pt-5 pb-3 shrink-0 border-b">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <FileSpreadsheet className="h-6 w-6 text-emerald-500 shrink-0" />
                            <div>
                                <DialogTitle className="text-xl">Import Preview</DialogTitle>
                                <DialogDescription className="mt-1 text-sm">
                                    Review tenant profiles and receipts before importing
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

                {/* Split Pane Content — Match BillsModal layout */}
                <div className="flex-1 min-h-0 flex">
                    {/* LEFT PANE: Tenant List — Match BillsModal left pane */}
                    <div className="w-[380px] lg:w-[420px] border-r bg-muted/30 flex flex-col shrink-0">
                        <div className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider shrink-0 border-b bg-muted/50 flex items-center justify-between">
                            <span>Tenants ({filteredTenants.length})</span>
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 text-xs"
                                onClick={toggleAll}
                            >
                                {selectedTargets.size === filteredTenants.length && filteredTenants.length > 0
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
                                    placeholder="Search name, ID, phone, company"
                                    className="pl-9"
                                />
                            </div>
                        </div>

                        <ScrollArea className="flex-1">
                            <div className="p-2 space-y-1.5">
                                {filteredTenants.length === 0 ? (
                                    <div className="text-sm text-muted-foreground p-3">
                                        No tenants found.
                                    </div>
                                ) : (
                                    filteredTenants.map((tenant) => {
                                        const targetKey = makeTargetKey(tenant.file, tenant.tenantId);
                                        const isSelected = selectedTargets.has(targetKey);
                                        const isActive = active === targetKey;
                                        const profile = tenant.profile;
                                        const receiptCount = tenant.receipts.length;

                                        return (
                                            <div
                                                key={targetKey}
                                                onClick={() => setSelectedTenant(tenant)}
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
                                                            toggleTarget(targetKey);
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
                                                                    {profile.tenantName || 'Unnamed Tenant'}
                                                                </div>
                                                                <div className="text-xs text-muted-foreground mt-0.5">
                                                                    {profile.tenantId}
                                                                    {profile.Room && ` • Room ${profile.Room}`}
                                                                </div>
                                                            </div>
                                                            <Badge
                                                                className={cn(
                                                                    getStatusTone(profile.Status || 'Active'),
                                                                    "text-[10px] h-5 px-1.5 shrink-0"
                                                                )}
                                                            >
                                                                {(profile.Status || 'Active').toUpperCase()}
                                                            </Badge>
                                                        </div>

                                                        <div className="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
                                                            <span>{receiptCount} receipt{receiptCount !== 1 ? 's' : ''}</span>
                                                            {profile.Phone && (
                                                                <span>• {profile.Phone}</span>
                                                            )}
                                                        </div>

                                                        <div className="mt-1 text-xs text-muted-foreground">
                                                            Rent {formatCurrency(profile.Rent)}
                                                            {profile.Water && ` • Water ${formatCurrency(profile.Water)}`}
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Active indicator — Match PreviewDialog */}
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

                    {/* RIGHT PANE: Receipts Table — Match BillsModal right pane */}
                    <div className="flex-1 flex flex-col min-w-0 bg-background">
                        {selectedTenant ? (
                            <>
                                {/* Tenant Header — Compact, Match BillsModal bill header */}
                                <div className="px-5 py-3 border-b bg-muted/20 shrink-0">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                                                <Upload className="h-5 w-5 text-primary" />
                                            </div>
                                            <div>
                                                <h3 className="font-semibold text-base">
                                                    {selectedTenant.profile.tenantName || 'Unnamed Tenant'}
                                                </h3>
                                                <p className="text-xs text-muted-foreground">
                                                    {selectedTenant.profile.tenantId}
                                                    {selectedTenant.profile.Company && ` • ${selectedTenant.profile.Company}`}
                                                    {selectedTenant.profile.Phone && ` • ${selectedTenant.profile.Phone}`}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Badge
                                                className={cn(
                                                    getStatusTone(selectedTenant.profile.Status || 'Active'),
                                                    "text-[10px] h-5 px-1.5"
                                                )}
                                            >
                                                {(selectedTenant.profile.Status || 'Active').toUpperCase()}
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
                                                        <TableRow key={`${receipt.BillNo}-${idx}`}>
                                                            <TableCell className="font-medium">
                                                                {receipt.BillNo}
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
                                                                        getStatusTone(receipt.receiptStatus || 'ACTIVE'),
                                                                        "text-[10px] h-5 px-1.5"
                                                                    )}
                                                                >
                                                                    {(receipt.receiptStatus || 'ACTIVE').toUpperCase()}
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

                {/* Footer — Match BillsModal footer style */}
                <div className="px-6 py-4 shrink-0 flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">
                        {stats.selected} of {stats.total} tenant{stats.total !== 1 ? 's' : ''} selected for import
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
                            size="sm"
                            onClick={handleConfirm}
                            disabled={selectedTargets.size === 0 || isExecuting}
                        >
                            {isExecuting ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <Check className="mr-2 h-4 w-4" />
                            )}
                            Import {selectedTargets.size > 0 && `(${selectedTargets.size})`}
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>

        {/* Status Override Dialog */}
        <Dialog open={statusDialogOpen} onOpenChange={setStatusDialogOpen}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>Archived tenant detected</DialogTitle>
                    <DialogDescription>
                        Some selected Excel records are marked Archived. Select the final
                        tenant status before importing.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
                    {Array.from(selectedTargets).map((targetKey) => {
                        const tenant = allTenants.find(
                            (item) => makeTargetKey(item.file, item.tenantId) === targetKey
                        );

                        if (tenant?.profile.Status?.trim().toUpperCase() !== "ARCHIVED") {
                            return null;
                        }

                        return (
                            <div key={targetKey} className="rounded-md border p-3">
                                <p className="mb-2 font-medium">{tenant.profile.tenantName}</p>
                                <div className="flex gap-2">
                                    {(["Active", "Inactive", "Archived"] as const).map((status) => (
                                        <Button
                                            key={status}
                                            type="button"
                                            size="sm"
                                            variant={targetStatuses[targetKey] === status ? "default" : "outline"}
                                            onClick={() =>
                                                setTargetStatuses((current) => ({
                                                    ...current,
                                                    [targetKey]: status,
                                                }))
                                            }
                                        >
                                            {status}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="flex justify-end gap-2 mt-4">
                    <Button
                        variant="outline"
                        onClick={() => setStatusDialogOpen(false)}
                        disabled={isExecuting}
                    >
                        Cancel
                    </Button>
                    <Button onClick={executeImport} disabled={isExecuting}>
                        {isExecuting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Importing...
                            </>
                        ) : "Confirm Import"}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
        </>
    );
}
