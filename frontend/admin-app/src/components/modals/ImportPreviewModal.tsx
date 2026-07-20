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
import { Loader2, Search, FileSpreadsheet, AlertCircle, Check, AlertTriangle, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import { importExecute, type PreviewResponse } from './importService';
import { toast } from 'sonner';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

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
    const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
    const [targetStatuses, setTargetStatuses] = useState<Record<string, TenantStatus>>({});
    
    // Conflict Resolutions
    const [idResolutions, setIdResolutions] = useState<Record<string, string>>({});
    const [receiptStrategies, setReceiptStrategies] = useState<Record<string, string>>({});
    const [pinHandling, setPinHandling] = useState<'prompt' | 'skip' | 'assign_random'>('assign_random');

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
        const nextStatuses: Record<string, TenantStatus> = {};
        const nextIdResolutions: Record<string, string> = {};
        const nextReceiptStrategies: Record<string, string> = {};
        const nextSelected = new Set<string>();

        allTenants.forEach((tenant) => {
            const key = makeTargetKey(tenant.file, tenant.tenantId);
            const importedStatus = tenant.profile.Status?.trim().toUpperCase();

            nextStatuses[key] = importedStatus === "ARCHIVED"
                ? "Active"
                : (tenant.profile.Status?.trim().replace(/^./, c => c.toUpperCase()) as TenantStatus || "Active");
                
            // Check conflicts
            const conflicts = previewData?.conflicts?.[tenant.file]?.[tenant.tenantId];
            if (conflicts) {
                if (conflicts.matches?.length > 0) {
                    nextIdResolutions[key] = "SKIP"; // Do not auto-select UPDATE_EXISTING
                } else {
                    nextIdResolutions[key] = "CREATE_NEW";
                }
                
                if (conflicts.receiptConflicts?.length > 0) {
                    nextReceiptStrategies[key] = "SKIP"; // Default to skip receipt conflicts
                } else {
                    nextReceiptStrategies[key] = "MERGE_RECEIPTS_ONLY";
                }
            } else {
                nextIdResolutions[key] = "CREATE_NEW";
                nextReceiptStrategies[key] = "MERGE_RECEIPTS_ONLY";
                nextSelected.add(key); // Auto-select non-conflicting
            }
        });
        
        setTargetStatuses(nextStatuses);
        setIdResolutions(nextIdResolutions);
        setReceiptStrategies(nextReceiptStrategies);
        setSelectedTargets(nextSelected);
    }, [allTenants, previewData]);

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

        setConfirmDialogOpen(true);
    };

    const executeImport = async () => {
        setIsExecuting(true);
        try {
            const targets = Array.from(selectedTargets);
            const selectedStatusMap = Object.fromEntries(
                targets.map((target) => [target, targetStatuses[target] || "Active"])
            );

            const result = await importExecute(
                files, 
                targets, 
                selectedStatusMap,
                idResolutions,
                {}, // pinResolutions - using auto-assign for now
                pinHandling,
                receiptStrategies
            );
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
        
    const activeConflicts = selectedTenant 
        ? previewData?.conflicts?.[selectedTenant.file]?.[selectedTenant.tenantId]
        : null;

    return (
        <>
        <Dialog open={open} onOpenChange={onOpenChange}>
            {/* Match PreviewDialog / BillsModal sizing pattern exactly */}
            <DialogContent className="max-w-[95vw] xl:max-w-[1400px] h-[92vh] p-0 flex flex-col gap-0 overflow-hidden">
                {/* Header */}
                <DialogHeader className="px-6 pt-5 pb-3 shrink-0 border-b">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <FileSpreadsheet className="h-6 w-6 text-emerald-500 shrink-0" />
                            <div>
                                <DialogTitle className="text-xl">Import Preview & Resolutions</DialogTitle>
                                <DialogDescription className="mt-1 text-sm">
                                    Review data, resolve conflicts, and confirm import actions.
                                </DialogDescription>
                            </div>
                        </div>
                        <div className="flex flex-wrap items-center justify-end gap-2">
                            <Badge className="bg-blue-100 text-blue-700 border-blue-200">
                                {stats.total} Tenant{stats.total !== 1 ? 's' : ''}
                            </Badge>
                            <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">
                                {stats.selected} Selected
                            </Badge>
                            {previewData?.requires_resolution && (
                                <Badge className="bg-amber-100 text-amber-700 border-amber-200 flex gap-1">
                                    <AlertTriangle className="w-3 h-3" /> Conflicts Detected
                                </Badge>
                            )}
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
                                    placeholder="Search name, ID, phone..."
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
                                        
                                        const hasConflicts = !!previewData?.conflicts?.[tenant.file]?.[tenant.tenantId];

                                        return (
                                            <div
                                                key={targetKey}
                                                onClick={() => setSelectedTenant(tenant)}
                                                className={cn(
                                                    "group relative rounded-lg border p-3 cursor-pointer transition-all",
                                                    "hover:bg-accent hover:border-accent-foreground/20",
                                                    isActive && "bg-primary/10 border-primary/50 ring-1 ring-primary/30",
                                                    !isActive && "bg-card border-border",
                                                    hasConflicts && !isActive && "border-amber-200 bg-amber-50/30"
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
                                                                <div className="font-semibold text-sm truncate flex items-center gap-2">
                                                                    {profile.tenantName || 'Unnamed Tenant'}
                                                                    {hasConflicts && <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />}
                                                                </div>
                                                                <div className="text-xs text-muted-foreground mt-0.5">
                                                                    {profile.tenantId}
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

                                                        {idResolutions[targetKey] && (
                                                            <div className="mt-2 text-[11px] font-medium text-muted-foreground">
                                                                Action: <span className="text-primary">{idResolutions[targetKey].replace(/_/g, ' ')}</span>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* Active indicator */}
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

                    {/* RIGHT PANE: Details & Resolutions */}
                    <div className="flex-1 flex flex-col min-w-0 bg-background overflow-auto">
                        {selectedTenant ? (
                            <div className="p-6 space-y-6">
                                {/* Tenant Overview */}
                                <div>
                                    <h3 className="text-lg font-semibold flex items-center gap-2">
                                        {selectedTenant.profile.tenantName || 'Unnamed Tenant'}
                                        <Badge variant="outline">{selectedTenant.profile.tenantId}</Badge>
                                    </h3>
                                    <div className="grid grid-cols-2 gap-4 mt-4 text-sm">
                                        <div><span className="text-muted-foreground">Phone:</span> {selectedTenant.profile.Phone || '-'}</div>
                                        <div><span className="text-muted-foreground">Email:</span> {selectedTenant.profile.Email || '-'}</div>
                                        <div><span className="text-muted-foreground">Meter ID:</span> {selectedTenant.profile.meterId || '-'}</div>
                                        <div><span className="text-muted-foreground">Company:</span> {selectedTenant.profile.Company || '-'}</div>
                                    </div>
                                </div>
                                
                                <Separator />

                                {/* Resolution Settings (If Selected) */}
                                <div className={cn("space-y-4", !selectedTargets.has(active) && "opacity-50 pointer-events-none")}>
                                    <h4 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                                        {activeConflicts ? <AlertTriangle className="h-4 w-4 text-amber-500" /> : <ShieldAlert className="h-4 w-4 text-emerald-500" />}
                                        Import Strategy
                                    </h4>

                                    {activeConflicts?.matches && activeConflicts.matches.length > 0 && (
                                        <Alert variant="destructive" className="bg-amber-50 border-amber-200 text-amber-900">
                                            <AlertCircle className="h-4 w-4 !text-amber-600" />
                                            <AlertTitle>Tenant Profile Conflict</AlertTitle>
                                            <AlertDescription className="text-amber-800">
                                                Matches found for: {activeConflicts.matches.map(m => m.type).join(', ')}.
                                                Please choose how to handle this tenant.
                                            </AlertDescription>
                                        </Alert>
                                    )}

                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium">Tenant Action</label>
                                        <Select
                                            value={idResolutions[active] || "CREATE_NEW"}
                                            onValueChange={(val) => setIdResolutions(p => ({ ...p, [active]: val }))}
                                        >
                                            <SelectTrigger className="w-[300px]">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="CREATE_NEW">Create as New Tenant</SelectItem>
                                                {(activeConflicts?.matches?.length ?? 0) > 0 && (
                                                    <SelectItem value="UPDATE_EXISTING">Update Existing Profile</SelectItem>
                                                )}
                                                <SelectItem value="MERGE_RECEIPTS_ONLY">Import Receipts Only</SelectItem>
                                                <SelectItem value="SKIP">Skip Tenant</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        {(idResolutions[active] || "CREATE_NEW") === "CREATE_NEW" && previewData?.predicted_next_tenant_id && (
                                            <div className="text-xs text-muted-foreground mt-1">
                                                <span className="font-semibold text-primary">New Assigned Code:</span> T{String(previewData.predicted_next_tenant_id).padStart(3, '0')} (ID: {previewData.predicted_next_tenant_id})
                                                <br/>
                                                <span className="text-[11px] opacity-80">*ID might shift if multiple new tenants are created at once.</span>
                                            </div>
                                        )}
                                    </div>
                                    
                                    {activeConflicts?.receiptConflicts && activeConflicts.receiptConflicts.length > 0 && (
                                        <Alert variant="destructive" className="bg-amber-50 border-amber-200 text-amber-900 mt-4">
                                            <AlertCircle className="h-4 w-4 !text-amber-600" />
                                            <AlertTitle>Receipt Conflicts ({activeConflicts.receiptConflicts.length})</AlertTitle>
                                            <AlertDescription className="text-amber-800">
                                                Some receipts already exist in the system (Duplicate Bill No or Month).
                                            </AlertDescription>
                                        </Alert>
                                    )}

                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium">Receipt Strategy</label>
                                        <Select
                                            value={receiptStrategies[active] || "MERGE_RECEIPTS_ONLY"}
                                            onValueChange={(val) => setReceiptStrategies(p => ({ ...p, [active]: val }))}
                                            disabled={idResolutions[active] === "SKIP"}
                                        >
                                            <SelectTrigger className="w-[300px]">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="MERGE_RECEIPTS_ONLY">Add / Update Uploaded Receipts</SelectItem>
                                                <SelectItem value="REPLACE_RECEIPTS">Wipe & Replace ALL Receipts</SelectItem>
                                                <SelectItem value="SKIP">Skip Receipts</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                                
                                <Separator />

                                {/* Receipts Table */}
                                <div>
                                    <h4 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground mb-4">
                                        Receipts Preview ({selectedTenant.receipts.length})
                                    </h4>
                                    <div className="border rounded-lg overflow-hidden">
                                        <Table>
                                            <TableHeader className="bg-muted/50">
                                                <TableRow>
                                                    <TableHead className="w-[100px]">Bill No</TableHead>
                                                    <TableHead>Month</TableHead>
                                                    <TableHead>Date</TableHead>
                                                    <TableHead className="text-right">Total</TableHead>
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {selectedTenant.receipts.slice(0, 5).map((receipt, idx) => (
                                                    <TableRow key={idx}>
                                                        <TableCell className="font-medium">{receipt.BillNo}</TableCell>
                                                        <TableCell>{receipt.Month}</TableCell>
                                                        <TableCell>{receipt.Date}</TableCell>
                                                        <TableCell className="text-right font-medium">{formatCurrency(receipt.Total)}</TableCell>
                                                    </TableRow>
                                                ))}
                                                {selectedTenant.receipts.length > 5 && (
                                                    <TableRow>
                                                        <TableCell colSpan={4} className="text-center text-muted-foreground bg-muted/20">
                                                            + {selectedTenant.receipts.length - 5} more receipts...
                                                        </TableCell>
                                                    </TableRow>
                                                )}
                                                {selectedTenant.receipts.length === 0 && (
                                                    <TableRow>
                                                        <TableCell colSpan={4} className="text-center text-muted-foreground">
                                                            No receipts to import.
                                                        </TableCell>
                                                    </TableRow>
                                                )}
                                            </TableBody>
                                        </Table>
                                    </div>
                                </div>
                                
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                                <AlertCircle className="h-10 w-10 mb-3 opacity-40" />
                                <p className="text-sm">Select a tenant to preview and resolve conflicts</p>
                            </div>
                        )}
                    </div>
                </div>

                <Separator />

                {/* Footer */}
                <div className="px-6 py-4 shrink-0 flex items-center justify-between bg-muted/10">
                    <div className="flex items-center gap-4">
                        <p className="text-sm font-medium">
                            {stats.selected} of {stats.total} tenants selected
                        </p>
                        
                        <div className="flex items-center gap-2 border-l pl-4">
                            <span className="text-sm text-muted-foreground">PIN Strategy:</span>
                            <Select value={pinHandling} onValueChange={(val: any) => setPinHandling(val)}>
                                <SelectTrigger className="w-[160px] h-8">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="assign_random">Auto-assign Random</SelectItem>
                                    <SelectItem value="skip">Skip PINs</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>
                    
                    <div className="flex gap-2">
                        <Button
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                        >
                            Cancel
                        </Button>
                        <Button
                            onClick={handleConfirm}
                            disabled={selectedTargets.size === 0 || isExecuting}
                            className="bg-primary hover:bg-primary/90"
                        >
                            {isExecuting ? (
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                                <Check className="mr-2 h-4 w-4" />
                            )}
                            Execute Import ({selectedTargets.size})
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
                        Some selected records are marked Archived. Select the final tenant status before importing.
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
                    <Button variant="outline" onClick={() => setStatusDialogOpen(false)} disabled={isExecuting}>Cancel</Button>
                    <Button onClick={() => { setStatusDialogOpen(false); setConfirmDialogOpen(true); }} disabled={isExecuting}>
                        Continue
                    </Button>
                </div>
            </DialogContent>
        </Dialog>

        {/* Import Confirmation Dialog */}
        <Dialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle className="text-destructive flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5" />
                        Import Confirmation
                    </DialogTitle>
                    <DialogDescription>
                        You are about to execute a destructive import operation. Please review the summary below.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="rounded-lg border bg-muted/30 p-4 space-y-2 text-sm">
                        <p><strong>{stats.selected}</strong> tenants selected for import.</p>
                        <ul className="list-disc pl-5 space-y-1 text-muted-foreground">
                            <li>Tenants to Create/Update: <strong>{Array.from(selectedTargets).filter(k => idResolutions[k] !== 'SKIP').length}</strong></li>
                            <li>Tenants Skipped: <strong>{Array.from(selectedTargets).filter(k => idResolutions[k] === 'SKIP').length}</strong></li>
                            <li>Receipts to Import: <strong>{stats.totalReceipts}</strong></li>
                        </ul>
                    </div>
                    
                    <Alert variant="destructive" className="bg-destructive/10 text-destructive border-destructive/20">
                        <AlertDescription>
                            This action will modify existing tenant data and cannot be undone except by backup restore.
                        </AlertDescription>
                    </Alert>
                </div>

                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setConfirmDialogOpen(false)} disabled={isExecuting}>
                        Cancel
                    </Button>
                    <Button variant="destructive" onClick={executeImport} disabled={isExecuting}>
                        {isExecuting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : "Confirm Import"}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
        </>
    );
}
