import { FileText, Eye, Download, Pencil, Archive, Trash2, RotateCcw, Check, MessageCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/services/api';
import type { Receipt } from '@/types';
import { useToast } from '@/hooks/useToast';
import { useState } from 'react';
import PaymentModal from '@/components/modals/PaymentModal';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface ReceiptRowProps {
  receipt: Receipt;
  onAction: () => void;
  onPreview: (data: { billNo: string; tenantId: number }) => void;
  onEdit: (data: { billNo: string; tenantId: number }) => void;
  variant?: 'history' | 'archive';
  onUpdatePayment?: (billNo: string, status: "PENDING" | "PARTIAL" | "PAID" | "ADVANCE", amount: number) => void;
  /** When true the receipt belongs to a tenant whose profile is currently archived.
   *  Restore is blocked and a prompt directs the admin to restore the tenant first. */
  ownerTenantIsArchived?: boolean;
  /** Display name of the owning tenant — used in the blocked-restore prompt. */
  ownerTenantName?: string;
}

export default function ReceiptRow({ receipt, onAction, onPreview, onEdit, variant = 'history', onUpdatePayment, ownerTenantIsArchived = false, ownerTenantName }: ReceiptRowProps) {
  const toast = useToast();
  const [confirmAction, setConfirmAction] = useState<string | null>(null);

  const currTotal = receipt.Total || 0;
  const prevArr = receipt.previousArrears || 0;
  const grandTotal = currTotal + prevArr;
  const amtRecv = receipt.amountReceived || 0;
  const balance = grandTotal - amtRecv;
  const advanceAmount = balance < 0 ? Math.abs(balance) : 0;

  const [paymentModalOpen, setPaymentModalOpen] = useState(false);

  const handleUpdatePayment = async (status: "PENDING" | "PARTIAL" | "PAID" | "ADVANCE", amount: number) => {
    try {
      if (onUpdatePayment) {
        onUpdatePayment(receipt.Bill, status, amount);
      } else {
        await api.updatePaymentStatus(receipt.TenantId, receipt.Bill, {
          paymentStatus: status,
          amountReceived: amount,
        });
        toast.success(`Payment updated to ${status}`);
        onAction();
      }
    } catch {
      toast.error('Failed to update payment status');
    }
  };

  const handleArchive = async () => {
    try {
      await api.archiveBill(receipt.TenantId, receipt.Bill);
      toast.success('Receipt archived');
      onAction();
    } catch {
      toast.error('Failed to archive receipt');
    }
    setConfirmAction(null);
  };

  const handleRestore = async () => {
    try {
      await api.restoreBill(receipt.TenantId, receipt.Bill);
      toast.success('Receipt restored');
      onAction();
    } catch {
      toast.error('Failed to restore receipt');
    }
    setConfirmAction(null);
  };

  const handleDelete = async () => {
    try {
      await api.permanentlyDeleteBill(receipt.TenantId, receipt.Bill);
      toast.success('Receipt permanently deleted');
      onAction();
    } catch {
      toast.error('Failed to delete receipt');
    }
    setConfirmAction(null);
  };

  const handleWhatsApp = async () => {
    try {
      const data = await api.sendWhatsApp(receipt.TenantId, receipt.Bill);
      if (data.url) {
        window.open(data.url, '_blank');
      }
    } catch {
      toast.error('Failed to generate WhatsApp link');
    }
  };

  const handleDownload = () => {
    const url = api.getPDFDownloadUrl(receipt.TenantId, receipt.Bill);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Receipt_${receipt.Bill}.pdf`;
    a.click();
  };

  const statusConfig = {
    PAID: { bg: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300', label: 'Paid', icon: Check },
    PARTIAL: { bg: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300', label: 'Partial', icon: Check },
    ADVANCE: { bg: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300', label: 'Advance', icon: Check },
    PENDING: { bg: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300', label: 'Pending', icon: RotateCcw },
  };

  const status = statusConfig[receipt.paymentStatus as keyof typeof statusConfig] || statusConfig.PENDING;
  const StatusIcon = status.icon;

  return (
    <>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3 px-4 border-b transition-colors hover:bg-accent/50">
        {/* Left: Tenant info */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center">
            <FileText size={18} />
          </div>
          <div className="min-w-0">
            <h6 className="font-semibold text-sm truncate">{receipt.Tenant}</h6>
            <div className="text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1 mr-2">
                <span className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono text-xs">
                  #{receipt.Bill}
                </span>
              </span>
              <span>{receipt.Date}</span>
            </div>
          </div>
        </div>

        {/* Center: Amount */}
        <div className="flex items-center gap-4 md:gap-6">
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Total Payable</div>
            <div className="font-bold text-base">₹{grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            <div className="text-xs text-green-600 dark:text-green-400">
              Paid: ₹{amtRecv.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            {balance > 0 && (
              <div className="text-xs text-red-500 font-medium">
                Due: ₹{balance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            )}
            {balance < 0 && (
              <div className="text-xs text-cyan-500 font-medium">
                Advance: ₹{advanceAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            )}
          </div>
          <div>
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium cursor-pointer transition-opacity hover:opacity-80 ${status.bg}`}
              onClick={() => setPaymentModalOpen(true)}
              title="Update Payment"
            >
              <StatusIcon size={12} />
              {status.label}
            </span>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setPaymentModalOpen(true)}
            title="Update Payment"
          >
            <Check size={14} className="text-green-500" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleWhatsApp} title="Send WhatsApp">
            <MessageCircle size={14} className="text-green-500" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground" onClick={() => onPreview({ billNo: receipt.Bill, tenantId: receipt.TenantId })} title="Preview">
            <Eye size={14} />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-yellow-500 hover:text-yellow-600 hover:bg-yellow-500/10" onClick={() => onEdit({ billNo: receipt.Bill, tenantId: receipt.TenantId })} title="Edit">
            <Pencil size={14} className="text-yellow-500" />
          </Button>
          {variant === 'archive' ? (
            <>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setConfirmAction('restore')}
                title="Restore"
              >
                <RotateCcw size={14} className="text-blue-500" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={() => setConfirmAction('delete')}
                title="Delete Permanently"
              >
                <Trash2 size={14} className="text-red-500" />
              </Button>
            </>
          ) : (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setConfirmAction('archive')}
              title="Archive"
            >
              <Archive size={14} className="text-red-500" />
            </Button>
          )}
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleDownload} title="Download PDF">
            <Download size={14} className="text-green-500" />
          </Button>
        </div>
      </div>

      {/* Confirm Archive */}
      <AlertDialog open={confirmAction === 'archive'} onOpenChange={() => setConfirmAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Archive Receipt?</AlertDialogTitle>
            <AlertDialogDescription>
              Receipt #{receipt.Bill} will be moved to Archived Receipts.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleArchive} className="bg-red-500 hover:bg-red-600">
              Archive
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Blocked Restore — receipt belongs to an archived tenant profile */}
      <AlertDialog open={confirmAction === 'restore' && ownerTenantIsArchived} onOpenChange={() => setConfirmAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <RotateCcw className="h-5 w-5 text-amber-500" />
              Cannot Restore Receipt
            </AlertDialogTitle>
            <AlertDialogDescription asChild>
              <div className="space-y-2 text-sm">
                <p>
                  Receipt <span className="font-semibold font-mono">#{receipt.Bill}</span> belongs to tenant profile{' '}
                  <span className="font-semibold">{ownerTenantName ?? receipt.Tenant}</span>, which is currently <span className="font-semibold text-amber-600">Archived</span>.
                </p>
                <p>
                  Individual receipts cannot be restored while their tenant profile remains archived.
                  To restore this receipt, first restore the tenant profile{' '}
                  <span className="font-semibold">{ownerTenantName ?? receipt.Tenant}</span> — that will
                  automatically restore all linked receipts including this one.
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogAction onClick={() => setConfirmAction(null)}>
              Understood
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Normal Restore Confirmation — receipt belongs to an active tenant (orphan archived bill) */}
      <AlertDialog open={confirmAction === 'restore' && !ownerTenantIsArchived} onOpenChange={() => setConfirmAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restore Receipt?</AlertDialogTitle>
            <AlertDialogDescription>
              Receipt <span className="font-semibold font-mono">#{receipt.Bill}</span> will be moved back to Active Receipts.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRestore}>
              Restore
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Confirm Delete */}
      <AlertDialog open={confirmAction === 'delete'} onOpenChange={() => setConfirmAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Permanently?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. Receipt #{receipt.Bill} will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-500 hover:bg-red-600">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <PaymentModal
        open={paymentModalOpen}
        onOpenChange={setPaymentModalOpen}
        bill={{
          Bill: receipt.Bill,
          Total: receipt.Total,
          PreviousArrears: receipt.previousArrears,
          AmountReceived: receipt.amountReceived,
          PaymentStatus: receipt.paymentStatus,
        }}
        onUpdate={handleUpdatePayment}
      />
    </>
  );
}
