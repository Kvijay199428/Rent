import { useState } from 'react';
import { RotateCcw, ChevronDown, ChevronUp, Trash2, AlertTriangle, ShieldAlert } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api } from '@/services/api';
import type { Tenant, Receipt, PermanentDeleteResult } from '@/types';
import { useToast } from '@/hooks/useToast';
import ReceiptRow from '@/components/shared/ReceiptRow';
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';

interface ArchiveTenantCardProps {
  tenant: Tenant;
  /** Only receipts whose TenantId === tenant.id — grouped by the parent Archive page. */
  receipts: Receipt[];
  onRefresh: () => void;
  onPreview: (data: { billNo: string; tenantId: number }) => void;
  onEdit: (data: { billNo: string; tenantId: number }) => void;
  onPermanentDelete?: (result: PermanentDeleteResult) => void;
}

export function ArchiveTenantCard({
  tenant,
  receipts,
  onRefresh,
  onPreview,
  onEdit,
  onPermanentDelete,
}: ArchiveTenantCardProps) {
  const toast = useToast();
  const [open, setOpen] = useState(true);
  const [confirmRestore, setConfirmRestore] = useState(false);
  const [restoring, setRestoring] = useState(false);

  // Permanent delete state — 2-stage dialog
  const [permDeleteStage, setPermDeleteStage] = useState<0 | 1 | 2>(0); // 0=closed, 1=warning, 2=confirm
  const [confirmText, setConfirmText] = useState('');
  const [permDeleting, setPermDeleting] = useState(false);

  const handleRestoreTenant = async () => {
    try {
      setRestoring(true);
      // POST /admin/api/tenants/{tenantId}/restore — dedicated endpoint, not DELETE ?action=restore
      const response = await api.restoreTenant(Number(tenant.id));

      // Use the restored tenant name from the response payload if available
      const restoredName =
        (response as { data?: { tenant?: { name?: string } } })?.data?.tenant?.name ?? tenant.name;

      toast.success(`Tenant "${restoredName}" restored successfully`);
      setConfirmRestore(false);
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to restore tenant');
    } finally {
      setRestoring(false);
    }
  };

  const openPermDeleteDialog = () => {
    setConfirmText('');
    setPermDeleteStage(1);
  };

  const closePermDeleteDialog = () => {
    setPermDeleteStage(0);
    setConfirmText('');
  };

  const isConfirmValid =
    confirmText.trim() === tenant.name.trim() || confirmText.trim().toUpperCase() === 'DELETE';

  const handlePermanentDelete = async () => {
    if (!isConfirmValid || permDeleting) return;
    try {
      setPermDeleting(true);
      const result = await api.permanentlyDeleteArchivedTenant(Number(tenant.id));
      closePermDeleteDialog();
      toast.success(
        `Tenant "${result.tenantName}" permanently deleted. Recovery snapshot: ${result.snapshotId} (expires ${new Date(result.expiresAt).toLocaleDateString()})`,
      );
      if (onPermanentDelete) onPermanentDelete(result);
      onRefresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Permanent deletion failed');
    } finally {
      setPermDeleting(false);
    }
  };

  return (
    <>
      <Card className="overflow-hidden">
        {/* Tenant header */}
        <div className="p-4 flex items-start justify-between gap-4 bg-muted/20">
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base font-semibold truncate">{tenant.name}</h2>
              <span className="px-2 py-0.5 rounded-md text-xs border font-mono">
                ID {tenant.id}
              </span>
              <span className="px-2 py-0.5 rounded-md text-xs border text-amber-700 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-300">
                {tenant.status}
              </span>
            </div>

            <div className="text-sm text-muted-foreground">
              Phone: {tenant.phone || '—'} · Email: {tenant.email || '—'} · Meter: {tenant.meterId || '—'}
            </div>

            <div className="text-xs text-muted-foreground">
              Room: {tenant.roomNumber || '—'} · Company: {tenant.company || '—'} · Rent: ₹{tenant.rent ?? 0}
            </div>

            {tenant.viewToken && (
              <div className="text-xs text-muted-foreground break-all font-mono">
                Token: {tenant.viewToken}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setOpen((v) => !v)}
              className="gap-1.5"
            >
              {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              {open ? 'Hide' : 'Show'} {receipts.length} Bills
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setConfirmRestore(true)}
              disabled={restoring}
              className="gap-1.5"
            >
              <RotateCcw className="h-4 w-4" />
              {restoring ? 'Restoring...' : 'Restore Tenant'}
            </Button>

            {/* Permanent Delete button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-red-600 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-900/20"
              onClick={openPermDeleteDialog}
              title="Permanently delete tenant and all data"
              disabled={permDeleting}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Receipt rows — only receipts belonging to this tenant (grouped by TenantId in Archive page) */}
        {open && (
          <CardContent className="p-0">
            {receipts.length === 0 ? (
              <div className="p-4 text-sm text-muted-foreground">
                No receipts linked to tenant ID {tenant.id}.
              </div>
            ) : (
              receipts.map((receipt) => (
                <ReceiptRow
                  key={`${receipt.TenantId}-${receipt.Bill}`}
                  receipt={receipt}
                  onAction={onRefresh}
                  onPreview={onPreview}
                  onEdit={onEdit}
                  variant="archive"
                  ownerTenantIsArchived={true}
                  ownerTenantName={tenant.name}
                />
              ))
            )}
          </CardContent>
        )}
      </Card>

      {/* Restore confirmation dialog */}
      <AlertDialog open={confirmRestore} onOpenChange={setConfirmRestore}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Restore Tenant?</AlertDialogTitle>
            <AlertDialogDescription>
              This will restore <strong>{tenant.name}</strong> (ID {tenant.id}) and all linked
              archived receipts back to active status.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={restoring}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRestoreTenant} disabled={restoring}>
              {restoring ? 'Restoring...' : 'Restore'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* ── Permanent Delete Dialog — Stage 1: Warning ─────────────────────── */}
      <Dialog open={permDeleteStage === 1} onOpenChange={() => closePermDeleteDialog()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <ShieldAlert className="h-5 w-5" />
              Permanently Delete Tenant
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="flex items-start gap-3 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <AlertTriangle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
              <div className="text-sm text-red-700 dark:text-red-300 space-y-1">
                <p className="font-semibold">This action will permanently erase:</p>
                <ul className="list-disc list-inside space-y-0.5 text-xs">
                  <li>Tenant profile for <strong>{tenant.name}</strong> (ID {tenant.id})</li>
                  <li>All {receipts.length} linked receipt(s) and PDF files</li>
                  <li>All occupant records and KYC documents</li>
                  <li>Tenant portal access, PIN history, and sessions</li>
                </ul>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-sm text-blue-700 dark:text-blue-300">
              <p className="font-semibold">Recovery via Backups</p>
              <p className="text-xs mt-1">
                A recovery snapshot will be saved automatically before deletion. You can restore
                the tenant from <strong>Backups → Deleted Tenants</strong> until the configured
                retention deadline expires.
              </p>
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={closePermDeleteDialog}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => setPermDeleteStage(2)}
            >
              Continue to Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Permanent Delete Dialog — Stage 2: Typed confirmation ─────────── */}
      <Dialog open={permDeleteStage === 2} onOpenChange={() => closePermDeleteDialog()}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <Trash2 className="h-5 w-5" />
              Confirm Permanent Deletion
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <p className="text-sm text-muted-foreground">
              Type the exact tenant name{' '}
              <code className="px-1 py-0.5 rounded bg-muted font-mono text-xs">{tenant.name}</code>{' '}
              or{' '}
              <code className="px-1 py-0.5 rounded bg-muted font-mono text-xs">DELETE</code>{' '}
              to enable the delete button.
            </p>

            <Input
              placeholder={`Type "${tenant.name}" or DELETE`}
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className={isConfirmValid ? 'border-red-400 focus-visible:ring-red-400' : ''}
              autoFocus
            />

            <p className="text-xs text-muted-foreground">
              After deletion, recovery is only possible from the tenant recovery snapshot
              (visible in <strong>Backups → Deleted Tenants</strong>) until the configured
              retention period expires. After expiry, the data is irrecoverable.
            </p>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setPermDeleteStage(1)} disabled={permDeleting}>
              Back
            </Button>
            <Button
              variant="destructive"
              onClick={handlePermanentDelete}
              disabled={!isConfirmValid || permDeleting}
            >
              {permDeleting ? 'Deleting...' : 'Permanently Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default ArchiveTenantCard;
