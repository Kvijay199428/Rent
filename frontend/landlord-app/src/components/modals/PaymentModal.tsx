import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

interface PaymentModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    bill: {
        Bill: string;
        Total: number;
        PreviousArrears: number;
        AmountReceived: number | null;
        PaymentStatus: string;
    };
    onUpdate: (status: "PENDING" | "PARTIAL" | "PAID" | "ADVANCE", amount: number) => void;
}

export default function PaymentModal({ open, onOpenChange, bill, onUpdate }: PaymentModalProps) {
    const grandTotal = Number(bill.Total || 0) + Number(bill.PreviousArrears || 0);
    const currentReceived = bill.AmountReceived != null ? Number(bill.AmountReceived) : 0;

    const [amount, setAmount] = useState<string>(currentReceived.toString());
    const [selectedStatus, setSelectedStatus] = useState<string>(bill.PaymentStatus || "PENDING");

    useEffect(() => {
        setAmount(currentReceived.toString());
        setSelectedStatus(bill.PaymentStatus || "PENDING");
    }, [bill, open]);

    // Auto-calculate status based on amount
    const calculateStatus = (amt: number): "PENDING" | "PARTIAL" | "PAID" | "ADVANCE" => {
        if (amt <= 0) return "PENDING";
        if (amt < grandTotal) return "PARTIAL";
        if (amt === grandTotal) return "PAID";
        return "ADVANCE";
    };

    const handleAmountChange = (val: string) => {
        setAmount(val);
        const num = parseFloat(val) || 0;
        setSelectedStatus(calculateStatus(num));
    };

    const handleStatusClick = (status: "PENDING" | "PARTIAL" | "PAID" | "ADVANCE") => {
        setSelectedStatus(status);
        // Set default amount based on status
        switch (status) {
            case "PENDING": setAmount("0"); break;
            case "PARTIAL": setAmount(Math.min(currentReceived || grandTotal / 2, grandTotal - 1).toString()); break;
            case "PAID": setAmount(grandTotal.toString()); break;
            case "ADVANCE": setAmount(Math.max(currentReceived, grandTotal + 100).toString()); break;
        }
    };

    const handleSubmit = () => {
        const numAmount = parseFloat(amount) || 0;
        const finalStatus = calculateStatus(numAmount);
        onUpdate(finalStatus, numAmount);
        onOpenChange(false);
    };

    const statusOptions: { value: "PENDING" | "PARTIAL" | "PAID" | "ADVANCE"; label: string; color: string }[] = [
        { value: "PENDING", label: "PENDING", color: "bg-red-100 text-red-700" },
        { value: "PARTIAL", label: "PARTIAL", color: "bg-amber-100 text-amber-700" },
        { value: "PAID", label: "PAID", color: "bg-green-100 text-green-700" },
        { value: "ADVANCE", label: "ADVANCE", color: "bg-emerald-100 text-emerald-700" },
    ];

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-md">
                <DialogHeader>
                    <DialogTitle>Update Payment - Bill {bill.Bill}</DialogTitle>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    {/* Grand Total Display */}
                    <div className="flex justify-between items-center p-3 bg-muted rounded-lg">
                        <span className="text-sm font-medium">Grand Total:</span>
                        <span className="text-lg font-bold">₹{grandTotal.toFixed(2)}</span>
                    </div>

                    {/* Status Selection */}
                    <div className="grid grid-cols-2 gap-2">
                        {statusOptions.map((opt) => (
                            <button
                                key={opt.value}
                                onClick={() => handleStatusClick(opt.value)}
                                className={`p-3 rounded-lg border-2 text-sm font-medium transition-all ${selectedStatus === opt.value
                                        ? "border-primary ring-2 ring-primary/20"
                                        : "border-border hover:border-primary/50"
                                    }`}
                            >
                                <Badge className={opt.color}>{opt.label}</Badge>
                            </button>
                        ))}
                    </div>

                    {/* Amount Input */}
                    <div className="space-y-2">
                        <Label htmlFor="amount">Amount Received (₹)</Label>
                        <Input
                            id="amount"
                            type="number"
                            step="0.01"
                            value={amount}
                            onChange={(e) => handleAmountChange(e.target.value)}
                            placeholder="Enter amount received"
                        />
                        <p className="text-xs text-muted-foreground">
                            {selectedStatus === "PENDING" && "No payment received"}
                            {selectedStatus === "PARTIAL" && `Balance due: ₹${(grandTotal - parseFloat(amount || "0")).toFixed(2)}`}
                            {selectedStatus === "PAID" && "Payment complete"}
                            {selectedStatus === "ADVANCE" && `Advance: ₹${(parseFloat(amount || "0") - grandTotal).toFixed(2)}`}
                        </p>
                    </div>
                </div>

                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
                    <Button onClick={handleSubmit}>
                        Update to {selectedStatus}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}