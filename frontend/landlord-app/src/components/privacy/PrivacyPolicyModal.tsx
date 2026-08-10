import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { AlertTriangle, FileText, ShieldCheck } from 'lucide-react';
import { BrandWave } from '@shared/loading/BrandWave';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ROUTES } from '@/lib/routes';
import MarkdownView from '@/components/privacy/MarkdownView';

interface PolicyInfo {
  version: string;
  effectiveDate: string;
  url: string;
  content: string;
}

interface PrivacyPolicyModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAgree: () => void;
}

export default function PrivacyPolicyModal({ open, onOpenChange, onAgree }: PrivacyPolicyModalProps) {
  const [policy, setPolicy] = useState<PolicyInfo | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    let active = true;
    fetch(ROUTES.LANDLORDAPIPRIVACYPOLICY)
      .then((res) => res.json())
      .then((data) => {
        if (!active) return;
        if (data?.content) {
          setPolicy(data);
          setError('');
        } else {
          setPolicy(null);
          setError('Privacy Policy content is unavailable right now.');
        }
      })
      .catch(() => {
        if (!active) return;
        setPolicy(null);
        setError('Unable to load the Privacy Policy. Please try again.');
      });
    return () => {
      active = false;
    };
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[85vh] flex flex-col p-0">
        <DialogHeader className="px-6 pt-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-full">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div>
              <DialogTitle>PROPAURA Privacy Policy</DialogTitle>
              <DialogDescription>
                {policy
                  ? `Version ${policy.version} — Effective ${policy.effectiveDate}`
                  : 'Landlord Account Creation'}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="overflow-y-auto px-6 py-4 border-y flex-1">
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {!policy && !error && (
            <div className="flex items-center justify-center py-16">
              <BrandWave label="Loading policy…" />
            </div>
          )}

          {policy?.content && <MarkdownView content={policy.content} />}
        </div>

        <DialogFooter className="px-6 py-4 items-center sm:justify-between">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <ShieldCheck className="h-4 w-4 text-green-600" />
            Issued in compliance with the Digital Personal Data Protection Act, 2023
          </div>
          <div className="flex gap-3">
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Close
            </Button>
            <Link to={ROUTES.LANDLORDPAGEPRIVACYPOLICY}>
              <Button variant="outline">Open Full Page</Button>
            </Link>
            <Button onClick={() => onAgree()}>I Agree</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
