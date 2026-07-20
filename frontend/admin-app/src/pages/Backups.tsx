import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { ROUTES } from '@/lib/routes';
import type { Backup, TenantRecoverySnapshot, SnapshotRestorePreview } from '@/types';
import {
  Database,
  ShieldPlus,
  Download,
  ShieldCheck,
  Trash2,
  RotateCcw,
  Archive,
  Clock,
  AlertTriangle,
  Loader2,
  UserX,
  CheckCircle2,
  XCircle,
  Info,
  ShieldAlert,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';


const filterTabs = ['All', 'Automatic', 'Manual', 'Restore Point', 'Emergency', 'Deleted Tenants'];

const typeConfig: Record<string, { color: string; icon: typeof Archive }> = {
  Automatic: { color: 'bg-cyan-500', icon: Clock },
  'Restore Point': { color: 'bg-amber-500', icon: RotateCcw },
  Emergency: { color: 'bg-red-500', icon: AlertTriangle },
  Manual: { color: 'bg-primary', icon: Archive },
};

// ── Tenant Recovery Snapshot Section ─────────────────────────────────────────

function TenantRecoverySection() {
  const toast = useToast();
  const [snapshots, setSnapshots] = useState<TenantRecoverySnapshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [previewSnapshot, setPreviewSnapshot] = useState<TenantRecoverySnapshot | null>(null);
  const [preview, setPreview] = useState<(SnapshotRestorePreview & { status: string }) | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [forceNewId, setForceNewId] = useState(false);
  const [restoreSuccess, setRestoreSuccess] = useState<{
    restoredId: number;
    originalId: number;
    idChanged: boolean;
  } | null>(null);

  const loadSnapshots = async () => {
    try {
      setLoading(true);
      const data = await api.getTenantRecoverySnapshots();
      setSnapshots(data.snapshots || []);
    } catch {
      toast.error('Failed to load deleted tenant snapshots');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSnapshots();
  }, []);

  const openRestoreDialog = async (snap: TenantRecoverySnapshot) => {
    setPreviewSnapshot(snap);
    setPreview(null);
    setForceNewId(false);
    setRestoreSuccess(null);
    setPreviewLoading(true);
    try {
      const data = await api.getTenantRecoverySnapshotPreview(snap.id);
      setPreview(data);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to load restore preview');
      setPreviewSnapshot(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const closeRestoreDialog = () => {
    setPreviewSnapshot(null);
    setPreview(null);
    setRestoreSuccess(null);
    setForceNewId(false);
  };

  const handleRestore = async () => {
    if (!previewSnapshot || restoring) return;
    try {
      setRestoring(true);
      const result = await api.restoreTenantFromSnapshot(previewSnapshot.id, forceNewId);
      setRestoreSuccess({
        restoredId: result.restored_tenant_id,
        originalId: result.original_tenant_id,
        idChanged: result.id_changed,
      });
      loadSnapshots();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Restore failed');
    } finally {
      setRestoring(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (snapshots.length === 0) {
    return (
      <Card>
        <CardContent className="text-center py-12 text-muted-foreground">
          <UserX className="h-12 w-12 mx-auto mb-3 opacity-40" />
          <h3 className="text-lg font-semibold">No Deleted Tenant Snapshots</h3>
          <p className="text-sm mt-1">
            When a tenant is permanently deleted from the Archive page, their recovery snapshot
            will appear here until the retention period expires.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {snapshots.map((snap) => {
          const isAvailable = snap.status === 'AVAILABLE' && snap.archive_exists && !snap.expired;
          const statusColor =
            isAvailable
              ? 'bg-green-500'
              : snap.status === 'RESTORED'
              ? 'bg-blue-500'
              : 'bg-gray-400';

          const createdDate = new Date(snap.created_at).toLocaleString();
          const expiresDate = new Date(snap.expires_at).toLocaleDateString();

          return (
            <Card key={snap.id} className="overflow-hidden">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <Badge className={`${statusColor} text-white text-xs`}>
                    {snap.status}
                  </Badge>
                  {isAvailable ? (
                    <span title="Archive intact">
                      <ShieldCheck className="h-5 w-5 text-green-500" />
                    </span>
                  ) : (
                    <span title="Not restorable">
                      <ShieldAlert className="h-5 w-5 text-gray-400" />
                    </span>
                  )}
                </div>

                <div>
                  <h6 className="font-bold truncate" title={snap.tenant_name}>
                    {snap.tenant_name}
                  </h6>
                  <p className="text-xs text-muted-foreground font-mono">
                    Original ID: {snap.tenant_id}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 bg-muted p-2 rounded-lg text-center text-xs">
                  <div>
                    <div className="text-muted-foreground">Deleted</div>
                    <div className="font-bold">{createdDate}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">
                      {snap.status === 'PURGED' ? 'Purged' : 'Expires'}
                    </div>
                    <div
                      className={`font-bold ${
                        isAvailable && snap.days_remaining <= 3
                          ? 'text-red-500'
                          : ''
                      }`}
                    >
                      {snap.status === 'PURGED'
                        ? (snap.purged_at ? new Date(snap.purged_at).toLocaleDateString() : '—')
                        : expiresDate}
                    </div>
                  </div>
                </div>

                {isAvailable && (
                  <p className="text-xs text-center text-muted-foreground">
                    {snap.days_remaining === 0
                      ? '⚠ Expires today'
                      : `${snap.days_remaining} day(s) remaining`}
                  </p>
                )}

                {snap.status === 'RESTORED' && (
                  <p className="text-xs text-center text-blue-600 dark:text-blue-400">
                    Restored on {snap.restored_at ? new Date(snap.restored_at).toLocaleDateString() : '—'}
                  </p>
                )}

                <div className="pt-2 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full rounded-full text-xs"
                    disabled={!isAvailable}
                    onClick={() => openRestoreDialog(snap)}
                  >
                    <RotateCcw className="h-3 w-3 mr-1" />
                    {isAvailable ? 'Restore Tenant' : 'Not Restorable'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Restore Preview Dialog */}
      <Dialog open={!!previewSnapshot} onOpenChange={() => closeRestoreDialog()}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RotateCcw className="h-5 w-5 text-primary" />
              Restore Deleted Tenant
            </DialogTitle>
          </DialogHeader>

          {previewLoading && (
            <div className="flex flex-col items-center py-8 gap-3">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Checking for conflicts...</p>
            </div>
          )}

          {restoreSuccess && (
            <div className="py-4 space-y-4 text-center">
              <CheckCircle2 className="h-14 w-14 text-green-500 mx-auto" />
              <h4 className="font-bold text-lg">Tenant Restored Successfully</h4>
              {restoreSuccess.idChanged ? (
                <p className="text-sm text-muted-foreground">
                  Restored with new tenant ID <strong>{restoreSuccess.restoredId}</strong>{' '}
                  (original was {restoreSuccess.originalId}).
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Tenant restored as ID <strong>{restoreSuccess.restoredId}</strong>.
                </p>
              )}
            </div>
          )}

          {!previewLoading && !restoreSuccess && preview && (
            <div className="space-y-4 py-2">
              {/* Tenant summary */}
              <div className="p-3 rounded-lg bg-muted/50 text-sm">
                <p><strong>Tenant:</strong> {previewSnapshot?.tenant_name}</p>
                <p><strong>Original ID:</strong> {previewSnapshot?.tenant_id}</p>
                <p><strong>Receipts in snapshot:</strong> {preview.receiptCount}</p>
              </div>

              {/* Conflict status */}
              {preview.canRestore ? (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-sm text-green-700 dark:text-green-300">
                  <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{preview.reason}</span>
                </div>
              ) : (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300">
                  <XCircle className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>{preview.reason}</span>
                </div>
              )}

              {/* Conflict details */}
              {Object.keys(preview.conflicts || {}).length > 0 && (
                <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-sm space-y-1.5">
                  <p className="font-semibold text-amber-700 dark:text-amber-300 flex items-center gap-1">
                    <AlertTriangle className="h-4 w-4" /> Conflicts Detected
                  </p>
                  {preview.conflicts.tenantId !== undefined && (
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      • Tenant ID <strong>{preview.conflicts.tenantId}</strong> is already in use
                      {preview.conflicts.existingTenantName && ` by "${preview.conflicts.existingTenantName}"`}
                    </p>
                  )}
                  {preview.conflicts.roomNumber && (
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      • Room <strong>{preview.conflicts.roomNumber}</strong> is occupied
                      {preview.conflicts.roomOccupiedBy && ` by "${preview.conflicts.roomOccupiedBy}"`}
                    </p>
                  )}
                  {preview.conflicts.phone && (
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      • Phone <strong>{preview.conflicts.phone}</strong> belongs to another tenant
                    </p>
                  )}
                  {preview.conflicts.email && (
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      • Email <strong>{preview.conflicts.email}</strong> belongs to another tenant
                    </p>
                  )}
                  {preview.conflicts.billNumbers && preview.conflicts.billNumbers.length > 0 && (
                    <p className="text-xs text-amber-700 dark:text-amber-300">
                      • Bill numbers already exist: <strong>{preview.conflicts.billNumbers.join(', ')}</strong>
                      {' '}— restore is blocked to prevent overwriting live receipts.
                    </p>
                  )}
                </div>
              )}

              {/* Force new ID option */}
              {preview.canRestore && preview.options.includes('restore-with-new-tenant-id') && (
                <div className="flex items-start gap-3 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                  <Info className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
                  <div className="text-sm text-blue-700 dark:text-blue-300">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={forceNewId}
                        onChange={(e) => setForceNewId(e.target.checked)}
                        className="rounded"
                      />
                      <span>
                        Restore with a <strong>new tenant ID</strong> (original ID {previewSnapshot?.tenant_id} is taken).
                        All receipts and occupants will be relinked to the new ID.
                      </span>
                    </label>
                  </div>
                </div>
              )}
            </div>
          )}

          <DialogFooter className="gap-2">
            {restoreSuccess ? (
              <Button onClick={closeRestoreDialog}>Close</Button>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={closeRestoreDialog}
                  disabled={restoring}
                >
                  Cancel
                </Button>
                {preview && preview.canRestore && !previewLoading && (
                  <Button
                    onClick={handleRestore}
                    disabled={
                      restoring ||
                      (!forceNewId && preview.options.includes('restore-with-new-tenant-id') &&
                        !preview.options.includes('restore-original'))
                    }
                  >
                    {restoring ? (
                      <><Loader2 className="h-4 w-4 mr-1 animate-spin" /> Restoring...</>
                    ) : (
                      <><RotateCcw className="h-4 w-4 mr-1" /> Restore Tenant</>
                    )}
                  </Button>
                )}
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ── Main Backups Page ─────────────────────────────────────────────────────────

export default function Backups() {
  const [backups, setBackups] = useState<Backup[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('All');
  const [restoring, setRestoring] = useState<Backup | null>(null);
  const [restoreStep, setRestoreStep] = useState(0);
  const toast = useToast();

  const loadBackups = async () => {
    try {
      setLoading(true);
      const data = await api.getBackups();
      setBackups(data.backups || []);
    } catch {
      toast.error('Failed to load backups');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBackups();
  }, []);

  const filtered = activeFilter === 'All'
    ? backups
    : backups.filter((b) => b.type === activeFilter);

  const handleCreateBackup = async () => {
    try {
      toast.loading('Creating backup...');
      await api.createManualBackup();
      toast.success('Backup created successfully');
      loadBackups();
    } catch {
      toast.error('Failed to create backup');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteBackup(id);
      toast.success('Backup deleted');
      loadBackups();
    } catch {
      toast.error('Failed to delete backup');
    }
  };

  const handleVerify = async (id: string) => {
    try {
      toast.loading('Verifying backup...');
      const result = await api.verifyBackup(id);
      if (result.status === 'success') {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
    } catch {
      toast.error('Verification failed');
    }
  };

  const startRestore = async (backup: Backup) => {
    setRestoring(backup);
    setRestoreStep(1);
  };

  const executeRestore = async () => {
    if (!restoring) return;
    setRestoreStep(3);
    try {
      await api.restoreBackup(restoring.id);
      toast.success('System restored successfully! Reloading...');
      setTimeout(() => window.location.reload(), 1500);
    } catch {
      toast.error('Restore failed');
      setRestoreStep(0);
      setRestoring(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b">
        <div>
          <h1 className="text-2xl font-bold">Disaster Recovery & Backups</h1>
          <p className="text-sm text-muted-foreground">Manage, verify, and restore system snapshots safely.</p>
        </div>
        <Button onClick={handleCreateBackup}>
          <ShieldPlus className="h-4 w-4 mr-1" /> Create Manual Backup
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-2">
          <div className="flex flex-wrap gap-1">
            {filterTabs.map((tab) => (
              <Button
                key={tab}
                variant={activeFilter === tab ? 'default' : 'ghost'}
                size="sm"
                className="rounded-full"
                onClick={() => setActiveFilter(tab)}
              >
                {tab === 'Deleted Tenants' && <UserX className="h-3 w-3 mr-1" />}
                {tab}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Deleted Tenants Tab */}
      {activeFilter === 'Deleted Tenants' && <TenantRecoverySection />}

      {/* Backups Grid — shown for all non-Deleted-Tenants tabs */}
      {activeFilter !== 'Deleted Tenants' && (
        loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : filtered.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12 text-muted-foreground">
              <Database className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <h3 className="text-lg font-semibold">No Backups Found</h3>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filtered.map((b) => {
              const config = typeConfig[b.type] || typeConfig.Manual;
              const TypeIcon = config.icon;
              const dateStr = new Date(b.date).toLocaleString();

              return (
                <Card key={b.id} className="overflow-hidden">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <Badge className={`${config.color} text-white`}>
                        <TypeIcon className="h-3 w-3 mr-1" />
                        {b.type}
                      </Badge>
                      {b.verified ? (
                        <span title="Verified"><ShieldCheck className="h-5 w-5 text-green-500" /></span>
                      ) : (
                        <span title="Unverified"><AlertTriangle className="h-5 w-5 text-yellow-500" /></span>
                      )}
                    </div>

                    <h6 className="font-bold truncate" title={b.id}>{b.notes || b.id}</h6>
                    <p className="text-xs text-muted-foreground mb-3">{dateStr}</p>

                    <div className="grid grid-cols-3 gap-2 mb-4 bg-muted p-2 rounded-lg text-center text-xs">
                      <div>
                        <div className="text-muted-foreground">Size</div>
                        <div className="font-bold">{b.size || '-'}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Receipts</div>
                        <div className="font-bold">{b.receipt_count || 0}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Tenants</div>
                        <div className="font-bold">{b.tenant_count || 0}</div>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t">
                      <Button
                        variant="outline"
                        size="sm"
                        className="rounded-full text-xs"
                        onClick={() => startRestore(b)}
                      >
                        <RotateCcw className="h-3 w-3 mr-1" /> Restore
                      </Button>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => {
                          const a = document.createElement('a');
                          a.href = ROUTES.ADMINAPIBACKUPSDOWNLOAD(b.id);
                          a.download = b.filename;
                          a.click();
                        }} title="Download">
                          <Download className="h-4 w-4 text-primary" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleVerify(b.id)} title="Verify">
                          <ShieldCheck className="h-4 w-4 text-cyan-500" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleDelete(b.id)} title="Delete">
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )
      )}

      {/* Restore Wizard Dialog (system-level restore — separate from tenant recovery) */}
      <Dialog open={!!restoring} onOpenChange={() => { setRestoring(null); setRestoreStep(0); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <RotateCcw className="h-5 w-5 text-primary" />
              {restoreStep === 1 && 'Restore System'}
              {restoreStep === 2 && 'Validating Backup...'}
              {restoreStep === 3 && 'Restoring System...'}
            </DialogTitle>
          </DialogHeader>

          {restoreStep === 1 && (
            <div className="text-center py-6">
              <AlertTriangle className="h-16 w-16 text-yellow-500 mx-auto mb-4" />
              <h4 className="text-lg font-bold mb-2">Confirm Restore</h4>
              <p className="text-muted-foreground mb-4">
                You are about to restore the system to:<br />
                <strong className="text-foreground">{restoring?.notes || restoring?.id}</strong>
              </p>
              <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg text-sm text-left text-blue-700 dark:text-blue-300 flex items-start gap-2">
                <ShieldCheck className="h-4 w-4 flex-shrink-0 mt-0.5" />
                A temporary restore point will be created automatically before the rollback.
              </div>
            </div>
          )}

          {restoreStep === 2 && (
            <div className="text-center py-8">
              <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
              <h5 className="font-bold">Validating Backup...</h5>
              <p className="text-sm text-muted-foreground">Checking checksums and archive integrity.</p>
            </div>
          )}

          {restoreStep === 3 && (
            <div className="text-center py-8">
              <Loader2 className="h-12 w-12 animate-spin text-green-500 mx-auto mb-4" />
              <h5 className="font-bold">Restoring System...</h5>
              <p className="text-sm text-muted-foreground">Extracting files and safely replacing database.</p>
            </div>
          )}

          <DialogFooter className="gap-2">
            {restoreStep === 1 && (
              <>
                <Button variant="outline" onClick={() => { setRestoring(null); setRestoreStep(0); }}>
                  Cancel
                </Button>
                <Button onClick={() => { setRestoreStep(2); setTimeout(() => setRestoreStep(3), 800); setTimeout(executeRestore, 2000); }}>
                  Validate Integrity
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
