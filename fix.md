Based on my thorough analysis of the source code, I've identified why the payment status system only supports "PAID" and "PENDING" and not all four statuses from domain.json ("PENDING", "PARTIAL", "PAID", "ADVANCE"). Let me provide you with a comprehensive breakdown of the issues and the required fixes.
🔍 ROOT CAUSE ANALYSIS
Issue 1: Frontend UI Only Has Two Buttons [PAID | PENDING]
From the ReceiptRow.tsx component, the payment toggle is a binary switch:
tsx
// ReceiptRow.tsx - ONLY two states
<button onClick={handlePaid}>Paid</button>
<button onClick={handlePending}>Pending</button>
There are no buttons for "PARTIAL" or "ADVANCE" statuses. The UI is hardcoded for binary toggling.
Issue 2: Frontend API Calls Hardcode Status Values
From api.ts:
TypeScript
// Only PAID or PENDING are ever sent
markPaid: async (billNo: string, amountReceived?: number) => {
  return api.updatePaymentStatus(billNo, {
    payment_status: "PAID",        // ← Hardcoded
    amount_received: amountReceived,
  });
},

markPending: async (billNo: string) => {
  return api.updatePaymentStatus(billNo, {
    payment_status: "PENDING",     // ← Hardcoded
    amount_received: 0,
  });
},
Issue 3: Backend update_payment_status() Auto-Calculates Status
From billing_service.py:
Python
def update_payment_status(billno, requested_status, amount_received=None):
    # ...
    state = resolve_payment_state(current_total, previous_arrears, amount_received)
    status = state["payment_status"]  # ← AUTO-CALCULATED, ignores requested_status!
    
    if requested_status in ["PENDING", "PARTIAL"]:
        status = requested_status  # ← Only PENDING/PARTIAL can override
The backend ignores the frontend's requested status for "PAID"/"ADVANCE" and auto-calculates based on amount comparison. This is actually correct logic, but the frontend never sends "PARTIAL" or "ADVANCE" as requested statuses, and there's no modal to input custom amounts.
Issue 4: No Amount Input Modal for Payment Processing
The user wants:
"when user clicks [PAID] it will give a popup modal to ask user to enter amount received"
But currently:
ReceiptRow.tsx calls onMarkPaid?.(row.Bill) — no amount parameter
No modal exists to input received amount
The BillsModal.tsx shows payment info but has no payment action buttons
✅ COMPLETE SOLUTION
Here's what needs to be changed across all files:
FILE 1: frontend/admin-app/src/services/api.ts
Replace the binary markPaid/markPending with a unified updatePayment that accepts any status and amount:
TypeScript
// REPLACE markPaid and markPending with:
updatePayment: async (
  billNo: string, 
  paymentStatus: "PENDING" | "PARTIAL" | "PAID" | "ADVANCE", 
  amountReceived?: number
): Promise<{ status: string }> => {
  return api.updatePaymentStatus(billNo, {
    payment_status: paymentStatus,
    amount_received: amountReceived,
  });
},
FILE 2: frontend/admin-app/src/components/shared/ReceiptRow.tsx
Replace the binary toggle with a dropdown or button group supporting all 4 statuses, plus a payment modal trigger:
tsx
import { useState } from "react";
import PaymentModal from "@/components/modals/PaymentModal"; // NEW COMPONENT

// ... inside ReceiptRow component:
const [paymentModalOpen, setPaymentModalOpen] = useState(false);

// Replace the simple PAID/PENDING buttons with:
<div className="flex items-center gap-2">
  <Badge 
    className={getStatusTone(row.PaymentStatus)}
    onClick={() => setPaymentModalOpen(true)}
  >
    {row.PaymentStatus || "PENDING"}
  </Badge>
  
  {/* Quick actions */}
  <Button size="sm" variant="outline" onClick={() => setPaymentModalOpen(true)}>
    Update Payment
  </Button>
</div>

<PaymentModal
  open={paymentModalOpen}
  onOpenChange={setPaymentModalOpen}
  bill={row}
  onUpdate={(status, amount) => onUpdatePayment?.(row.Bill, status, amount)}
/>
FILE 3: NEW frontend/admin-app/src/components/modals/PaymentModal.tsx
Create this new modal for payment input:
tsx
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
                className={`p-3 rounded-lg border-2 text-sm font-medium transition-all ${
                  selectedStatus === opt.value
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
FILE 4: frontend/admin-app/src/components/shared/ReceiptRow.tsx
Update props and handlers:
tsx
interface ReceiptRowProps {
  // ... existing props ...
  onUpdatePayment?: (billNo: string, status: "PENDING" | "PARTIAL" | "PAID" | "ADVANCE", amount: number) => void;
  // REMOVE: onMarkPaid, onMarkPending (or keep for backward compat)
}
FILE 5: frontend/admin-app/src/pages/Dashboard.tsx & History/Archive Pages
Update the payment handler:
tsx
// Replace markPaid/markPending calls with:
const handleUpdatePayment = async (
  billNo: string, 
  status: "PENDING" | "PARTIAL" | "PAID" | "ADVANCE", 
  amount: number
) => {
  try {
    await api.updatePayment(billNo, status, amount);
    toast.success(`Payment updated to ${status}`);
    loadData(); // Refresh
  } catch (err) {
    toast.error("Failed to update payment");
  }
};
FILE 6: Backend app/app/api/billing.py
The api_update_payment endpoint is already mostly correct. Just ensure it accepts all statuses:
Python
@router.post(Routes.ADMIN_API_BILLING_UPDATE_PAYMENT, name=Names.API_UPDATE_PAYMENT)
async def api_update_payment(billno: str, data: PaymentStatusUpdate, background_tasks: BackgroundTasks):
    try:
        status = (data.paymentstatus or "").strip().upper()
        # VALIDATE all 4 statuses from domain.json
        if status not in {"PAID", "PENDING", "PARTIAL", "ADVANCE"}:
            raise HTTPException(status_code=400, detail="Invalid payment status.")
        
        amount = data.amountreceived
        
        # Allow explicit status override with amount validation
        update_payment_status(billno, status, amount)
        background_tasks.add_task(create_full_backup, tag="payment_status")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
FILE 7: Backend app/app/services/billing_service.py
Update update_payment_status to respect explicit status when provided with valid amount:
Python
def update_payment_status(billno, requested_status, amount_received=None):
    from app.core.db import get_conn
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM receipts WHERE billno = ?", (billno,)).fetchone()
        if not row:
            raise ValueError("Receipt not found")
        
        current_total = float(row["total"])
        previous_arrears = float(row["previousarrears"])
        grand_total = round(current_total + previous_arrears, 2)
        
        # Determine final amount
        if amount_received is None:
            amount_received = grand_total if requested_status == "PAID" else 0.0
        
        amount_received = round(float(amount_received), 2)
        
        # VALIDATE: requested_status must match amount logic, OR auto-calculate
        calculated_status = "PENDING"
        if amount_received <= 0:
            calculated_status = "PENDING"
        elif amount_received < grand_total:
            calculated_status = "PARTIAL"
        elif amount_received == grand_total:
            calculated_status = "PAID"
        else:
            calculated_status = "ADVANCE"
        
        # Use requested status if it matches the amount logic, otherwise use calculated
        # This allows explicit control while preventing invalid combinations
        final_status = requested_status
        
        # Validate consistency (optional strict mode)
        if requested_status == "PAID" and amount_received != grand_total:
            raise ValueError(f"PAID status requires amount = {grand_total}, got {amount_received}")
        if requested_status == "PARTIAL" and (amount_received <= 0 or amount_received >= grand_total):
            raise ValueError(f"PARTIAL status requires 0 < amount < {grand_total}")
        if requested_status == "ADVANCE" and amount_received <= grand_total:
            raise ValueError(f"ADVANCE status requires amount > {grand_total}")
        if requested_status == "PENDING" and amount_received != 0:
            raise ValueError("PENDING status requires amount = 0")
        
        conn.execute("""
            UPDATE receipts 
            SET paymentstatus = ?, amountreceived = ?
            WHERE billno = ?
        """, (final_status, amount_received, billno))
        conn.commit()
    
    return final_status
📋 SUMMARY TABLE
Table
File	Change Type	Description
api.ts	Modify	Replace markPaid/markPending with unified updatePayment(status, amount)
ReceiptRow.tsx	Modify	Add PaymentModal trigger, remove binary toggle
NEW PaymentModal.tsx	Create	Modal for amount input with all 4 status buttons + auto-calculation
Dashboard.tsx	Modify	Update handler to pass (billNo, status, amount)
billing.py	Modify	Validate all 4 statuses in endpoint
billing_service.py	Modify	Add strict validation between status and amount
The core issue is that the frontend was designed with only 2 states in mind (binary toggle), while the backend's domain.json and database support 4 states. The fix requires both UI expansion (modal with amount input + 4 status buttons) and backend validation (ensure status/amount consistency).