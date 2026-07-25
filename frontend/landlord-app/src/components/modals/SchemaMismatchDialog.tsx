import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
    AlertTriangle,
    Download,
    X,
    CheckCircle2,
    XCircle,
    Sheet,
} from 'lucide-react';

// ─── Types ─────────────────────────────────────────────────────────

export type SchemaMismatchInfo = {
    /** The file name that failed validation */
    filename: string;
    /** What was expected (e.g. "Tenant_Profile, Rent_Receipts sheets") */
    expected?: string;
    /** What was actually found in the file */
    actual?: string;
    /** Specific missing sheets */
    missingSheets?: string[];
    /** Specific missing headers per sheet */
    missingHeaders?: Record<string, string[]>;
    /** Extra headers that are not recognized */
    extraHeaders?: Record<string, string[]>;
};

type SchemaMismatchDialogProps = {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    /** Single mismatch or list of mismatches (for multi-file upload) */
    mismatches: SchemaMismatchInfo | SchemaMismatchInfo[];
    /** Called when user clicks "Download Template" */
    onDownloadTemplate?: () => void;
    /** Called when user clicks "Try Again" */
    onRetry?: () => void;
};

// ─── Constants ───────────────────────────────────────────────────────

const EXPECTED_PROFILE_HEADERS = [
    'tenantId', 'tenantName', 'Phone', 'Email', 'Company', 'Address',
    'Room', 'meterId', 'PIN', 'Rent', 'Water', 'electricityRate',
    'additionalPersonRate', 'tankWater', 'Status',
];

const EXPECTED_RECEIPT_HEADERS = [
    'BillNo', 'tenantId', 'Month', 'Date', 'Previous', 'Current',
    'Units', 'Rent', 'Water', 'Electricity', 'Additional',
    'tankWater', 'Maintenance', 'Arrears', 'amountReceived',
    'Total', 'paymentStatus', 'receiptStatus',
];

const EXPECTED_SHEETS = ['Tenant_Profile', 'Rent_Receipts'];

// ─── Component ───────────────────────────────────────────────────────

export default function SchemaMismatchDialog({
    open,
    onOpenChange,
    mismatches,
    onDownloadTemplate,
    onRetry,
}: SchemaMismatchDialogProps) {
    const mismatchList = Array.isArray(mismatches) ? mismatches : [mismatches];

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-[600px] max-h-[85vh] p-0 flex flex-col gap-0 overflow-hidden">
                {/* Header */}
                <DialogHeader className="px-6 pt-5 pb-3 shrink-0 border-b bg-red-50/50">
                    <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-red-100 flex items-center justify-center shrink-0">
                            <AlertTriangle className="h-5 w-5 text-red-600" />
                        </div>
                        <div>
                            <DialogTitle className="text-lg text-red-800">
                                Schema Mismatch Detected
                            </DialogTitle>
                            <DialogDescription className="mt-0.5 text-sm text-red-600/80">
                                The uploaded file does not match the expected import schema
                            </DialogDescription>
                        </div>
                    </div>
                </DialogHeader>

                {/* Content */}
                <div className="flex-1 overflow-auto px-6 py-4 space-y-4">
                    {/* Summary */}
                    <div className="rounded-lg border border-red-200 bg-red-50/30 p-4">
                        <p className="text-sm text-red-800 leading-relaxed">
                            We could not process your import because the file structure does not
                            match what the system expects. Please compare your file against the
                            required schema below, or download the official template to ensure
                            compatibility.
                        </p>
                    </div>

                    {/* File-specific errors */}
                    {mismatchList.map((mismatch, idx) => (
                        <div
                            key={idx}
                            className="rounded-lg border border-amber-200 bg-amber-50/20 p-4 space-y-3"
                        >
                            <div className="flex items-center gap-2">
                                <XCircle className="h-4 w-4 text-red-500 shrink-0" />
                                <span className="text-sm font-medium text-red-700">
                                    {mismatch.filename}
                                </span>
                            </div>

                            {mismatch.missingSheets && mismatch.missingSheets.length > 0 && (
                                <div className="ml-6 space-y-1.5">
                                    <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide">
                                        Missing Sheets
                                    </p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {mismatch.missingSheets.map((sheet) => (
                                            <Badge
                                                key={sheet}
                                                variant="outline"
                                                className="bg-red-50 text-red-700 border-red-200 text-[11px]"
                                            >
                                                <X className="h-3 w-3 mr-1" />
                                                {sheet}
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {mismatch.missingHeaders &&
                                Object.entries(mismatch.missingHeaders).map(
                                    ([sheet, headers]) =>
                                        headers.length > 0 ? (
                                            <div key={sheet} className="ml-6 space-y-1.5">
                                                <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide">
                                                    Missing Headers in "{sheet}"
                                                </p>
                                                <div className="flex flex-wrap gap-1.5">
                                                    {headers.map((header) => (
                                                        <Badge
                                                            key={header}
                                                            variant="outline"
                                                            className="bg-red-50 text-red-700 border-red-200 text-[11px]"
                                                        >
                                                            <X className="h-3 w-3 mr-1" />
                                                            {header}
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </div>
                                        ) : null
                                )}

                            {mismatch.actual && (
                                <p className="ml-6 text-xs text-muted-foreground">
                                    Found: {mismatch.actual}
                                </p>
                            )}
                        </div>
                    ))}

                    <Separator />

                    {/* Expected Schema Reference */}
                    <div className="space-y-4">
                        <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                            <Sheet className="h-4 w-4 text-blue-500" />
                            Required Schema Reference
                        </h4>

                        {/* Expected Sheets */}
                        <div className="rounded-lg border p-3 space-y-2">
                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                Required Sheets
                            </p>
                            <div className="flex flex-wrap gap-2">
                                {EXPECTED_SHEETS.map((sheet) => (
                                    <Badge
                                        key={sheet}
                                        className="bg-green-50 text-green-700 border-green-200"
                                    >
                                        <CheckCircle2 className="h-3 w-3 mr-1" />
                                        {sheet}
                                    </Badge>
                                ))}
                            </div>
                        </div>

                        {/* Tenant_Profile headers */}
                        <div className="rounded-lg border p-3 space-y-2">
                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                Tenant_Profile Headers
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                                {EXPECTED_PROFILE_HEADERS.map((header) => (
                                    <code
                                        key={header}
                                        className="text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border"
                                    >
                                        {header}
                                    </code>
                                ))}
                            </div>
                        </div>

                        {/* Rent_Receipts headers */}
                        <div className="rounded-lg border p-3 space-y-2">
                            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                                Rent_Receipts Headers
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                                {EXPECTED_RECEIPT_HEADERS.map((header) => (
                                    <code
                                        key={header}
                                        className="text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border"
                                    >
                                        {header}
                                    </code>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                <Separator />

                {/* Footer */}
                <div className="px-6 py-4 shrink-0 flex items-center justify-between bg-muted/20">
                    <p className="text-xs text-muted-foreground">
                        Download the template to ensure your data is formatted correctly.
                    </p>
                    <div className="flex gap-2">
                        {onRetry && (
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                    onOpenChange(false);
                                    onRetry();
                                }}
                            >
                                Try Again
                            </Button>
                        )}
                        {onDownloadTemplate && (
                            <Button
                                size="sm"
                                onClick={() => {
                                    onDownloadTemplate();
                                    onOpenChange(false);
                                }}
                                className="bg-red-600 hover:bg-red-700 text-white"
                            >
                                <Download className="mr-2 h-4 w-4" />
                                Download Template
                            </Button>
                        )}
                        <Button
                            variant="ghost"
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
