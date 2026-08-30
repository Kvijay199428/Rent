import { useState, useEffect, useCallback } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Pencil, Trash2, Plus, Check } from "lucide-react";
import { api } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/useToast";
import type { Receipt, PaymentState, PaymentEntry } from "@/types";

interface PaymentModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    receipt: Receipt | null;
    /** Optional callback invoked after any payment mutation so parent can refresh. */
    onChange?: () => void;
}

function todayISO(): string {
    const d = new Date();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${m}-${day}`;
}

const statusConfig: Record<string, { label: string; color: string }> = {
    PAID: { label: "PAID", color: "bg-green-100 text-green-700" },
    PARTIAL: { label: "PARTIAL", color: "bg-amber-100 text-amber-700" },
    ADVANCE: { label: "ADVANCE", color: "bg-emerald-100 text-emerald-700" },
    PENDING: { label: "PENDING", color: "bg-red-100 text-red-700" },
};

export default function PaymentModal({ open, onOpenChange, receipt, onChange }: PaymentModalProps) {
    const { landlordUuid } = useAuth();
    const toast = useToast();

    const grandTotal = Number(receipt?.Total || 0) + Number(receipt?.previousArrears || 0);

    const [state, setState] = useState<PaymentState | null>(null);
    const [loading, setLoading] = useState(false);

    const [amount, setAmount] = useState<string>("");
    const [paymentDate, setPaymentDate] = useState<string>(todayISO());
    const [editingId, setEditingId] = useState<number | null>(null);

    const loadPayments = useCallback(async () => {
        if (!landlordUuid || !receipt) return;
        try {
            const data = await api.getPayments(landlordUuid, receipt.TenantId, receipt.Bill);
            setState(data);
        } catch {
            toast.error("Failed to load payments");
        }
    }, [landlordUuid, receipt?.TenantId, receipt?.Bill, toast]);

    useEffect(() => {
        if (open) {
            loadPayments();
        }
    }, [open, loadPayments]);

    if (!receipt) {
        return null;
    }

    const startEdit = (entry: PaymentEntry) => {
        setEditingId(entry.id);
        setAmount(entry.amount.toString());
        setPaymentDate(entry.paymentDate || todayISO());
    };

    const resetForm = () => {
        setEditingId(null);
        setAmount("");
        setPaymentDate(todayISO());
    };

    const handleSubmit = async () => {
        if (!landlordUuid || !receipt) return;
        const numAmount = parseFloat(amount) || 0;
        if (numAmount <= 0) {
            toast.error("Enter a valid payment amount");
            return;
        }
        if (paymentDate > todayISO()) {
            toast.error("Payment date cannot be in the future");
            return;
        }
        try {
            if (editingId != null) {
                await api.updatePayment(landlordUuid, receipt.TenantId, receipt.Bill, editingId, {
                    paymentDate,
                    amount: numAmount,
                });
                toast.success("Payment updated");
            } else {
                await api.createPayment(landlordUuid, receipt.TenantId, receipt.Bill, {
                    paymentDate,
                    amount: numAmount,
                });
                toast.success("Payment recorded");
            }
            resetForm();
            await loadPayments();
            onChange?.();
        } catch {
            toast.error("Failed to save payment");
        }
    };

    const handleDelete = async (paymentId: number) => {
        if (!landlordUuid || !receipt) return;
        try {
            await api.deletePayment(landlordUuid, receipt.TenantId, receipt.Bill, paymentId);
            toast.success("Payment deleted");
            await loadPayments();
            onChange?.();
        } catch {
            toast.error("Failed to delete payment");
        }
    };

    const numAmount = parseFloat(amount) || 0;
    const afterReceived = numAmount > 0
        ? (state ? state.totalReceived : Number(receipt.amountReceived || 0)) + numAmount
        : (state ? state.totalReceived : Number(receipt.amountReceived || 0));
    const afterBalance = Math.max(grandTotal - afterReceived, 0);
    const afterAdvance = Math.max(afterReceived - grandTotal, 0);

    const status = statusConfig[state?.paymentStatus || receipt.paymentStatus] || statusConfig.PENDING;

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Manage Payments - Bill {receipt.Bill}</DialogTitle>
                </DialogHeader>

                {/* Summary */}
                <div className="space-y-2 p-3 bg-muted rounded-lg text-sm">
                    <div className="flex justify-between items-center">
                        <span className="font-medium">Grand Total</span>
                        <span className="font-bold text-base">₹{grandTotal.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="font-medium">Received{state && state.paymentCount > 0 ? ` (${state.paymentCount})` : ""}</span>
                        <span className="text-green-600 font-medium">₹{(state ? state.totalReceived : Number(receipt.amountReceived || 0)).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="font-medium">Balance Due</span>
                        <span className="text-red-500 font-medium">₹{(state ? state.balanceDue : Math.max(grandTotal - Number(receipt.amountReceived || 0), 0)).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="font-medium">Status</span>
                        <Badge className={status.color}>{status.label}</Badge>
                    </div>
                </div>

                {/* Add / Edit form */}
                <div className="space-y-3 pt-2">
                    <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1.5">
                            <Label>Payment Date</Label>
                            <Input
                                type="date"
                                max={todayISO()}
                                value={paymentDate}
                                onChange={(e) => setPaymentDate(e.target.value)}
                            />
                        </div>
                        <div className="space-y-1.5">
                            <Label>Amount (₹)</Label>
                            <Input
                                type="number"
                                step="0.01"
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                                placeholder="Enter amount"
                            />
                        </div>
                    </div>

                    {/* Live preview after this payment */}
                    {numAmount > 0 && (
                        <div className="text-xs text-muted-foreground space-y-0.5 bg-accent/40 rounded p-2">
                            <div>After this payment → Received: <span className="font-semibold text-green-600">₹{afterReceived.toFixed(2)}</span></div>
                            <div>
                                {afterBalance > 0
                                    ? <>Balance due: <span className="font-semibold text-red-500">₹{afterBalance.toFixed(2)}</span></>
                                    : afterAdvance > 0
                                        ? <>Advance: <span className="font-semibold text-emerald-600">₹{afterAdvance.toFixed(2)}</span></>
                                        : <span className="font-semibold text-green-600">Fully paid</span>}
                            </div>
                            <div className="font-medium">
                                Status will be{" "}
                                {numAmount <= 0 ? "PENDING" : afterReceived < grandTotal ? "PARTIAL" : afterReceived === grandTotal ? "PAID" : "ADVANCE"}
                            </div>
                        </div>
                    )}

                    <div className="flex justify-end gap-2">
                        {editingId != null && (
                            <Button variant="outline" onClick={resetForm}>Cancel Edit</Button>
                        )}
                        <Button onClick={handleSubmit}>
                            {editingId != null ? <><Check size={14} /> Update Payment</> : <><Plus size={14} /> Add Payment</>}
                        </Button>
                    </div>
                </div>

                {/* Payment history */}
                {state && state.payments.length > 0 && (
                    <div className="pt-2">
                        <div className="text-sm font-semibold mb-2">Payment History</div>
                        <div className="border rounded-lg divide-y">
                            {state.payments.map((p) => (
                                <div key={p.id} className="flex items-center justify-between px-3 py-2 text-sm">
                                    <div>
                                        <div className="font-mono text-xs text-muted-foreground">{p.paymentDate}</div>
                                        <div className="font-semibold">₹{p.amount.toFixed(2)}</div>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 text-yellow-500"
                                            onClick={() => startEdit(p)}
                                            title="Edit"
                                        >
                                            <Pencil size={14} />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-7 w-7 text-red-500"
                                            onClick={() => handleDelete(p.id)}
                                            title="Delete"
                                        >
                                            <Trash2 size={14} />
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                <div className="flex justify-end pt-2">
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
