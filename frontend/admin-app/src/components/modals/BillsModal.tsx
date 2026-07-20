import { useEffect, useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, RefreshCw, Search, FileText, AlertCircle, Receipt } from 'lucide-react';
import { cn } from '@/lib/utils';
import ROUTES from '@/lib/routes';

export type TenantBill = {
    Bill: string;
    Month: string;
    Status: string;
    PaymentStatus: string;
    Total: number;
    PreviousArrears: number;
    AmountReceived: number | null;
};

type BillsModalProps = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    tenantId: number | null;
    tenantname?: string;
    bills: TenantBill[];
    loading?: boolean;
    selectedBill: TenantBill | null;
    onSelectBill: (bill: TenantBill | null) => void;
};

function getBillAmounts(bill: TenantBill | null) {
    const total = Number(bill?.Total || 0) + Number(bill?.PreviousArrears || 0);
    const received =
        bill?.AmountReceived != null
            ? Number(bill.AmountReceived)
            : (bill?.PaymentStatus || 'PENDING').toUpperCase() === 'PAID'
                ? total
                : 0;

    const due = Math.max(total - received, 0);
    const advance = Math.max(received - total, 0);

    return { total, received, due, advance };
}

function getBillTone(status: string) {
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

function formatMonthLabel(value?: string) {
    if (!value) return '-';
    const raw = String(value).trim();
    const d = new Date(raw);

    if (!Number.isNaN(d.getTime())) {
        return d.toLocaleDateString('en-GB', {
            month: 'short',
            year: 'numeric',
        });
    }

    return raw;
}

function getStatusBuckets(bills: TenantBill[]) {
    let due = 0;
    let partial = 0;
    let advance = 0;

    for (const bill of bills) {
        const status = (bill.PaymentStatus || 'PENDING').toUpperCase();
        const amt = getBillAmounts(bill);

        if (status === 'ADVANCE' || amt.advance > 0) {
            advance += amt.advance;
        } else if (status === 'PARTIAL') {
            partial += amt.due;
        } else if (status !== 'PAID' && amt.due > 0) {
            due += amt.due;
        }
    }

    return { due, partial, advance };
}

export default function BillsModal({
    open,
    onOpenChange,
    tenantId,
    tenantname,
    bills,
    loading = false,
    selectedBill,
    onSelectBill,
}: BillsModalProps) {
    const [iframeLoading, setIframeLoading] = useState(true);
    const [query, setQuery] = useState('');
    const [refreshKey, setRefreshKey] = useState(0);

    const stats = useMemo(() => getStatusBuckets(bills), [bills]);

    const filteredBills = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return bills;

        return bills.filter((bill) => {
            const month = formatMonthLabel(bill.Month).toLowerCase();
            const billNo = String(bill.Bill || '').toLowerCase();
            const status = String(bill.PaymentStatus || '').toLowerCase();
            return month.includes(q) || billNo.includes(q) || status.includes(q);
        });
    }, [bills, query]);

    useEffect(() => {
        if (!selectedBill && bills.length > 0 && open) {
            onSelectBill(bills[0]);
        }
    }, [selectedBill, bills, open, onSelectBill]);

    useEffect(() => {
        if (selectedBill && open) {
            setIframeLoading(true);
        }
    }, [selectedBill?.Bill, open, refreshKey]);

    const previewUrl = selectedBill && tenantId
        ? `${ROUTES.ADMINAPIPDFVIEW(tenantId, selectedBill.Bill)}?ts=${refreshKey}`
        : '';

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            {/* Match PreviewDialog sizing pattern exactly */}
            <DialogContent className="max-w-[95vw] xl:max-w-[1400px] h-[92vh] p-0 flex flex-col gap-0 overflow-hidden">
                {/* Match PreviewDialog header styling */}
                <DialogHeader className="px-6 pt-5 pb-3 shrink-0 border-b">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Receipt className="h-6 w-6 text-emerald-500 shrink-0" />
                            <div>
                                <DialogTitle className="text-xl">Bills - {tenantname || 'Tenant'}</DialogTitle>
                                <DialogDescription className="mt-1 text-sm">
                                    Receipt history with live PDF preview
                                </DialogDescription>
                            </div>
                        </div>
                        <div className="flex flex-wrap items-center justify-end gap-2">
                            <Badge className="bg-red-100 text-red-700 border-red-200">
                                Due ₹{stats.due.toFixed(2)}
                            </Badge>
                            <Badge className="bg-amber-100 text-amber-700 border-amber-200">
                                Partial ₹{stats.partial.toFixed(2)}
                            </Badge>
                            <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">
                                Advance ₹{stats.advance.toFixed(2)}
                            </Badge>
                        </div>
                    </div>
                </DialogHeader>

                {/* Split Pane Content - Match PreviewDialog layout */}
                <div className="flex-1 min-h-0 flex">
                    {/* LEFT PANE: Bills List - Match PreviewDialog left pane */}
                    <div className="w-[380px] lg:w-[420px] border-r bg-muted/30 flex flex-col shrink-0">
                        <div className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider shrink-0 border-b bg-muted/50">
                            Bills ({filteredBills.length})
                        </div>

                        <div className="shrink-0 border-b p-3 space-y-2">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    placeholder="Search month, bill no, status"
                                    className="pl-9"
                                />
                            </div>
                        </div>

                        <ScrollArea className="flex-1">
                            <div className="p-2 space-y-1.5">
                                {loading ? (
                                    <div className="flex items-center justify-center py-10">
                                        <Loader2 className="h-6 w-6 animate-spin text-primary" />
                                    </div>
                                ) : filteredBills.length === 0 ? (
                                    <div className="text-sm text-muted-foreground p-3">
                                        No bills found.
                                    </div>
                                ) : (
                                    filteredBills.map((bill) => {
                                        const status = (bill.PaymentStatus || 'PENDING').toUpperCase();
                                        const amt = getBillAmounts(bill);
                                        const active = selectedBill?.Bill === bill.Bill;

                                        return (
                                            <div
                                                key={bill.Bill}
                                                onClick={() => onSelectBill(bill)}
                                                className={cn(
                                                    "group relative rounded-lg border p-3 cursor-pointer transition-all",
                                                    "hover:bg-accent hover:border-accent-foreground/20",
                                                    active && "bg-primary/10 border-primary/50 ring-1 ring-primary/30",
                                                    !active && "bg-card border-border"
                                                )}
                                            >
                                                <div className="flex items-start justify-between gap-3">
                                                    <div className="min-w-0 flex-1">
                                                        <div className="font-semibold text-sm">
                                                            {formatMonthLabel(bill.Month)}
                                                        </div>
                                                        <div className="text-xs text-muted-foreground mt-1">
                                                            Bill {bill.Bill}
                                                        </div>
                                                    </div>

                                                    <Badge className={cn(getBillTone(status), "text-[10px] h-5 px-1.5")}>
                                                        {status}
                                                    </Badge>
                                                </div>

                                                <div className="mt-2 space-y-1">
                                                    {amt.due > 0 ? (
                                                        <div className="text-sm font-medium text-red-600">
                                                            Due ₹{amt.due.toFixed(2)}
                                                        </div>
                                                    ) : amt.advance > 0 ? (
                                                        <div className="text-sm font-medium text-emerald-600">
                                                            Advance ₹{amt.advance.toFixed(2)}
                                                        </div>
                                                    ) : (
                                                        <div className="text-sm font-medium text-green-600">
                                                            Paid
                                                        </div>
                                                    )}

                                                    <div className="text-xs text-muted-foreground">
                                                        Total ₹{amt.total.toFixed(2)} • Received ₹{amt.received.toFixed(2)}
                                                    </div>
                                                </div>

                                                {/* Active indicator - Match PreviewDialog */}
                                                {active && (
                                                    <div className="absolute left-0 top-3 bottom-3 w-0.5 bg-primary rounded-r-full" />
                                                )}
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </ScrollArea>
                    </div>

                    {/* RIGHT PANE: PDF Preview - Match PreviewDialog right pane */}
                    <div className="flex-1 flex flex-col min-w-0 bg-background">
                        {selectedBill ? (
                            <>
                                {/* Bill Header - Compact, Match PreviewDialog tenant header */}
                                <div className="px-5 py-3 border-b bg-muted/20 shrink-0">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                                                <FileText className="h-5 w-5 text-primary" />
                                            </div>
                                            <div>
                                                <h3 className="font-semibold text-base">
                                                    {formatMonthLabel(selectedBill.Month)}
                                                </h3>
                                                <p className="text-xs text-muted-foreground">
                                                    Bill No: {selectedBill.Bill} • {tenantname || 'Tenant'}
                                                </p>
                                            </div>
                                        </div>
                                        <Badge
                                            className={cn(
                                                getBillTone(selectedBill.PaymentStatus || 'PENDING'),
                                                "text-[10px] h-5 px-1.5"
                                            )}
                                        >
                                            {(selectedBill.PaymentStatus || 'PENDING').toUpperCase()}
                                        </Badge>
                                    </div>
                                </div>

                                {/* PDF Iframe - Full height, no extra ScrollArea wrapper */}
                                <div className="flex-1 min-h-0 bg-neutral-300/70 relative">
                                    {iframeLoading && (
                                        <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/70 backdrop-blur-sm">
                                            <Loader2 className="h-8 w-8 animate-spin text-primary" />
                                        </div>
                                    )}

                                    <iframe
                                        key={`${selectedBill.Bill}-${refreshKey}`}
                                        src={previewUrl}
                                        title={`Receipt ${selectedBill.Bill}`}
                                        className={cn(
                                            "w-full h-full border-0 transition-opacity duration-300",
                                            iframeLoading ? 'opacity-0' : 'opacity-100'
                                        )}
                                        onLoad={() => setIframeLoading(false)}
                                    />
                                </div>
                            </>
                        ) : (
                            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                                <AlertCircle className="h-10 w-10 mb-3 opacity-40" />
                                <p className="text-sm">Select a bill from the left panel to preview the PDF</p>
                            </div>
                        )}
                    </div>
                </div>

                <Separator />

                {/* Footer - Match PreviewDialog footer style */}
                <div className="px-6 py-4 shrink-0 flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">
                        {filteredBills.length} bill{filteredBills.length !== 1 ? 's' : ''} found
                    </p>
                    <div className="flex gap-2">
                        {selectedBill && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setRefreshKey((k) => k + 1)}
                            >
                                <RefreshCw className="mr-2 h-4 w-4" />
                                Refresh
                            </Button>
                        )}
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onOpenChange(false)}
                        >
                            Close
                        </Button>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    );
}
// import { useEffect, useMemo, useState } from 'react';
// import { Badge } from '@/components/ui/badge';
// import { Button } from '@/components/ui/button';
// import { Input } from '@/components/ui/input';
// import {
//     Dialog,
//     DialogContent,
//     DialogHeader,
//     DialogTitle,
// } from '@/components/ui/dialog';
// import { Loader2, RefreshCw, Search, Printer, Download } from 'lucide-react';

// export type TenantBill = {
//     Bill: string;
//     Month: string;
//     Status: string;
//     PaymentStatus: string;
//     Total: number;
//     PreviousArrears: number;
//     AmountReceived: number | null;
// };

// type BillsModalProps = {
//     open: boolean;
//     onOpenChange: (open: boolean) => void;
//     tenantname?: string;
//     bills: TenantBill[];
//     loading?: boolean;
//     selectedBill: TenantBill | null;
//     onSelectBill: (bill: TenantBill | null) => void;
// };

// function getBillAmounts(bill: TenantBill | null) {
//     const total = Number(bill?.Total || 0) + Number(bill?.PreviousArrears || 0);
//     const received =
//         bill?.AmountReceived != null
//             ? Number(bill.AmountReceived)
//             : (bill?.PaymentStatus || 'PENDING').toUpperCase() === 'PAID'
//                 ? total
//                 : 0;

//     const due = Math.max(total - received, 0);
//     const advance = Math.max(received - total, 0);

//     return { total, received, due, advance };
// }

// function getBillTone(status: string) {
//     switch ((status || '').toUpperCase()) {
//         case 'PAID':
//             return 'bg-green-50 text-green-700 border-green-200';
//         case 'ADVANCE':
//             return 'bg-emerald-50 text-emerald-700 border-emerald-200';
//         case 'PARTIAL':
//             return 'bg-amber-50 text-amber-700 border-amber-200';
//         default:
//             return 'bg-red-50 text-red-700 border-red-200';
//     }
// }

// function formatMonthLabel(value?: string) {
//     if (!value) return '-';
//     const raw = String(value).trim();
//     const d = new Date(raw);

//     if (!Number.isNaN(d.getTime())) {
//         return d.toLocaleDateString('en-GB', {
//             month: 'short',
//             year: 'numeric',
//         });
//     }

//     return raw;
// }

// function getStatusBuckets(bills: TenantBill[]) {
//     let due = 0;
//     let partial = 0;
//     let advance = 0;

//     for (const bill of bills) {
//         const status = (bill.PaymentStatus || 'PENDING').toUpperCase();
//         const amt = getBillAmounts(bill);

//         if (status === 'ADVANCE' || amt.advance > 0) {
//             advance += amt.advance;
//         } else if (status === 'PARTIAL') {
//             partial += amt.due;
//         } else if (status !== 'PAID' && amt.due > 0) {
//             due += amt.due;
//         }
//     }

//     return { due, partial, advance };
// }

// export default function BillsModal({
//     open,
//     onOpenChange,
//     tenantname,
//     bills,
//     loading = false,
//     selectedBill,
//     onSelectBill,
// }: BillsModalProps) {
//     const [iframeLoading, setIframeLoading] = useState(true);
//     const [query, setQuery] = useState('');
//     const [refreshKey, setRefreshKey] = useState(0);

//     const stats = useMemo(() => getStatusBuckets(bills), [bills]);

//     const filteredBills = useMemo(() => {
//         const q = query.trim().toLowerCase();
//         if (!q) return bills;

//         return bills.filter((bill) => {
//             const month = formatMonthLabel(bill.Month).toLowerCase();
//             const billNo = String(bill.Bill || '').toLowerCase();
//             const status = String(bill.PaymentStatus || '').toLowerCase();
//             return month.includes(q) || billNo.includes(q) || status.includes(q);
//         });
//     }, [bills, query]);

//     useEffect(() => {
//         if (!selectedBill && bills.length > 0 && open) {
//             onSelectBill(bills[0]);
//         }
//     }, [selectedBill, bills, open, onSelectBill]);

//     useEffect(() => {
//         if (selectedBill && open) {
//             setIframeLoading(true);
//         }
//     }, [selectedBill?.Bill, open, refreshKey]);

//     const basePath = window.location.pathname.startsWith('/rent') ? '/rent' : '';
//     const previewUrl = selectedBill
//         ? `${basePath}/admin/api/pdf/receipt/${selectedBill.Bill}/view?ts=${refreshKey}`
//         : '';

//     return (
//         <Dialog open={open} onOpenChange={onOpenChange}>
//             <DialogContent className="w-[98vw] !max-w-[98vw] h-[95vh] p-0 overflow-hidden">
//                 <div className="flex h-full min-h-0 flex-col">
//                     <DialogHeader className="shrink-0 border-b px-5 py-4 pr-16">
//                         <div className="flex flex-wrap items-start justify-between gap-4">
//                             <div className="min-w-0">
//                                 <DialogTitle className="text-lg">
//                                     Bills - {tenantname || 'Tenant'}
//                                 </DialogTitle>
//                                 <div className="text-sm text-muted-foreground mt-1">
//                                     Receipt history with live PDF preview
//                                 </div>
//                             </div>

//                             {selectedBill && (
//                                 <div className="min-w-0 max-w-full">
//                                     <div className="font-medium text-lg truncate">
//                                         {formatMonthLabel(selectedBill.Month)}: Bill No: {selectedBill.Bill}
//                                     </div>
//                                 </div>
//                             )}

//                             <div className="flex flex-wrap items-center justify-end gap-2 max-w-[calc(100%-3rem)]">
//                                 <Badge className="bg-red-100 text-red-700 border-red-200">
//                                     Due ₹{stats.due.toFixed(2)}
//                                 </Badge>
//                                 <Badge className="bg-amber-100 text-amber-700 border-amber-200">
//                                     Partial ₹{stats.partial.toFixed(2)}
//                                 </Badge>
//                                 <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">
//                                     Advance ₹{stats.advance.toFixed(2)}
//                                 </Badge>
//                             </div>
//                         </div>
//                     </DialogHeader>

//                     <div className="grid grid-cols-[300px_1fr] min-h-0 flex-1 overflow-hidden">
//                         <aside className="min-h-0 border-r bg-muted/20 flex flex-col">
//                             <div className="shrink-0 border-b p-4 space-y-3">
//                                 <div className="font-medium text-sm">Bills</div>

//                                 <div className="relative">
//                                     <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
//                                     <Input
//                                         value={query}
//                                         onChange={(e) => setQuery(e.target.value)}
//                                         placeholder="Search month, bill no, status"
//                                         className="pl-9"
//                                     />
//                                 </div>

//                             </div>

//                             <div className="min-h-0 flex-1 overflow-y-auto p-3 space-y-3">
//                                 {loading ? (
//                                     <div className="flex items-center justify-center py-10">
//                                         <Loader2 className="h-6 w-6 animate-spin text-primary" />
//                                     </div>
//                                 ) : filteredBills.length === 0 ? (
//                                     <div className="text-sm text-muted-foreground p-3">
//                                         No bills found.
//                                     </div>
//                                 ) : (
//                                     filteredBills.map((bill) => {
//                                         const status = (bill.PaymentStatus || 'PENDING').toUpperCase();
//                                         const amt = getBillAmounts(bill);
//                                         const active = selectedBill?.Bill === bill.Bill;

//                                         return (
//                                             <button
//                                                 key={bill.Bill}
//                                                 type="button"
//                                                 onClick={() => onSelectBill(bill)}
//                                                 className={`w-full rounded-xl border p-4 text-left transition ${active
//                                                     ? 'border-primary bg-primary/5 shadow-sm ring-1 ring-primary/20'
//                                                     : 'border-border bg-background hover:bg-accent'
//                                                     }`}
//                                             >
//                                                 <div className="flex items-start justify-between gap-3">
//                                                     <div className="min-w-0">
//                                                         <div className="font-semibold text-sm">
//                                                             {formatMonthLabel(bill.Month)}
//                                                         </div>
//                                                         <div className="text-xs text-muted-foreground mt-1">
//                                                             Bill {bill.Bill}
//                                                         </div>
//                                                     </div>


//                                                     <Badge className={getBillTone(status)}>
//                                                         {status}
//                                                     </Badge>
//                                                 </div>

//                                                 <div className="mt-3 space-y-1">
//                                                     {amt.due > 0 ? (
//                                                         <div className="text-sm font-medium text-red-600">
//                                                             Due ₹{amt.due.toFixed(2)}
//                                                         </div>
//                                                     ) : amt.advance > 0 ? (
//                                                         <div className="text-sm font-medium text-emerald-600">
//                                                             Advance ₹{amt.advance.toFixed(2)}
//                                                         </div>
//                                                     ) : (
//                                                         <div className="text-sm font-medium text-green-600">
//                                                             Paid
//                                                         </div>
//                                                     )}

//                                                     <div className="text-xs text-muted-foreground">
//                                                         Total ₹{amt.total.toFixed(2)} • Received ₹{amt.received.toFixed(2)}
//                                                     </div>
//                                                 </div>
//                                             </button>
//                                         );
//                                     })
//                                 )}
//                             </div>
//                         </aside>

//                         <section className="min-h-0 min-w-0 bg-neutral-300/70 flex flex-col">

//                             <div className="min-h-0 flex-1 overflow-auto p-2 md:p-3">
//                                 {selectedBill ? (
//                                     <div className="h-full flex justify-center">
//                                         <div className="w-full h-full bg-white rounded-md shadow-2xl overflow-hidden relative">
//                                             {iframeLoading && (
//                                                 <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/70 backdrop-blur-sm">
//                                                     <Loader2 className="h-8 w-8 animate-spin text-primary" />
//                                                 </div>
//                                             )}

//                                             <iframe
//                                                 key={`${selectedBill.Bill}-${refreshKey}`}
//                                                 src={previewUrl}
//                                                 title={`Receipt ${selectedBill.Bill}`}
//                                                 className={`w-full h-full border-0 transition-opacity duration-300 ${iframeLoading ? 'opacity-0' : 'opacity-100'
//                                                     }`}
//                                                 onLoad={() => setIframeLoading(false)}
//                                             />
//                                         </div>
//                                     </div>
//                                 ) : (
//                                     <div className="h-full flex items-center justify-center text-muted-foreground">
//                                         Select a bill from the left panel to preview the PDF
//                                     </div>
//                                 )}
//                             </div>
//                         </section>
//                     </div>
//                 </div>
//             </DialogContent>
//         </Dialog>
//     );
// }
