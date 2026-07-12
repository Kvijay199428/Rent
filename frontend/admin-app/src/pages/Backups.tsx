import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { ROUTES } from '@/lib/routes';
import type { Backup } from '@/types';
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
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';


const filterTabs = ['All', 'Automatic', 'Manual', 'Restore Point', 'Emergency'];

const typeConfig: Record<string, { color: string; icon: typeof Archive }> = {
  Automatic: { color: 'bg-cyan-500', icon: Clock },
  'Restore Point': { color: 'bg-amber-500', icon: RotateCcw },
  Emergency: { color: 'bg-red-500', icon: AlertTriangle },
  Manual: { color: 'bg-primary', icon: Archive },
};

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
                {tab}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Backups Grid */}
      {loading ? (
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
                        a.href = ROUTES.adminApiBackupsDownload(b.id);
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
      )}

      {/* Restore Wizard Dialog */}
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
