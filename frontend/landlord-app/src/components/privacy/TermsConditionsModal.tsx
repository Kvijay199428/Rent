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

interface TermsInfo {
  version: string;
  effectiveDate: string;
  url: string;
  content: string;
}

interface TermsConditionsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAgree: () => void;
}

export default function TermsConditionsModal({ open, onOpenChange, onAgree }: TermsConditionsModalProps) {
  const [terms, setTerms] = useState<TermsInfo | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    let active = true;
    fetch(ROUTES.LANDLORDAPITERMS)
      .then((res) => res.json())
      .then((data) => {
        if (!active) return;
        if (data?.content) {
          setTerms(data);
          setError('');
        } else {
          setTerms(null);
          setError('Terms and Conditions content is unavailable right now.');
        }
      })
      .catch(() => {
        if (!active) return;
        setTerms(null);
        setError('Unable to load the Terms and Conditions. Please try again.');
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
              <DialogTitle>PROPAURA Terms and Conditions</DialogTitle>
              <DialogDescription>
                {terms
                  ? `Version ${terms.version} — Effective ${terms.effectiveDate}`
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

          {!terms && !error && (
            <div className="flex items-center justify-center py-16">
              <BrandWave label="Loading terms…" />
            </div>
          )}

          {terms?.content && <MarkdownView content={terms.content} />}
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
            <Link to={ROUTES.LANDLORDPAGETERMS}>
              <Button variant="outline">Open Full Page</Button>
            </Link>
            <Button onClick={() => onAgree()}>I Agree</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
