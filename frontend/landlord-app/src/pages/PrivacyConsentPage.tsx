import { useEffect, useRef, useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Checkbox } from '@/components/ui/checkbox';
import { AlertTriangle, CheckCircle2, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { ROUTES } from '@/lib/routes';
import { useAuth } from '@/contexts/AuthContext';
import MarkdownView from '@/components/privacy/MarkdownView';
import { BrandWave } from '@shared/loading/BrandWave';
import LoadingOverlay from '@shared/loading/LoadingOverlay';

interface PolicyInfo {
  version: string;
  effectiveDate: string;
  url: string;
  content: string;
}

export default function PrivacyConsentPage() {
  const navigate = useNavigate();
  const { refreshMe, landlordUuid } = useAuth();
  const [policy, setPolicy] = useState<PolicyInfo | null>(null);
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    fetch(ROUTES.LANDLORDAPIPRIVACYPOLICY)
      .then((res) => res.json())
      .then((data) => {
        if (active && data?.content) setPolicy(data);
        else if (active) setError('Privacy Policy content is unavailable right now.');
      })
      .catch(() => active && setError('Unable to load the Privacy Policy. Please try again.'));
    return () => {
      active = false;
    };
  }, []);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 40) {
      // reached the end — nothing special, checkbox still explicit
    }
  };

  const handleAccept = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!agreed) {
      setError('You must read and accept the Privacy Policy to continue.');
      return;
    }
    if (!policy) {
      setError('Privacy Policy is still loading. Please try again.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(ROUTES.LANDLORDAPIAUTHPRIVACYCONSENT, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accepted: true, privacyVersion: policy.version }),
      });
      const data = await res.json().catch(() => null);

      if (!res.ok) {
        setError(data?.detail || 'Could not record your acceptance. Please try again.');
        return;
      }

      toast.success('Privacy Policy accepted', { description: 'Thank you. Redirecting to your dashboard...' });
      await refreshMe();
      const dest = landlordUuid ? `/${landlordUuid}/dashboard` : '/dashboard';
      setTimeout(() => navigate(dest, { replace: true }), 1200);
    } catch {
      setError('Network error. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        <Card className="shadow-xl">
          <CardHeader className="space-y-1">
            <div className="flex items-center justify-center mb-4">
              <div className="p-3 bg-primary/10 rounded-full">
                <ShieldCheck className="h-8 w-8 text-primary" />
              </div>
            </div>
            <CardTitle className="text-2xl text-center">Privacy Policy Consent Required</CardTitle>
            <CardDescription className="text-center">
              {policy
                ? `Version ${policy.version} — Effective ${policy.effectiveDate}`
                : 'Your account cannot be used until you accept the current Privacy Policy.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
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

            {policy?.content && (
              <>
                <div
                  ref={scrollRef}
                  onScroll={handleScroll}
                  className="border rounded-md max-h-72 overflow-y-auto p-4 bg-muted/30 text-sm mb-4"
                >
                  <MarkdownView content={policy.content} />
                </div>

                <p className="text-xs text-muted-foreground mb-4">
                  Read the complete policy on the{' '}
                  <Link to={ROUTES.LANDLORDPAGEPRIVACYPOLICY} className="text-primary underline underline-offset-2">
                    Privacy Policy page
                  </Link>
                  .
                </p>

                <form onSubmit={handleAccept} className="space-y-4">
                  <label className="flex items-start gap-3 rounded-md border p-3 cursor-pointer hover:bg-muted/50 transition-colors">
                    <Checkbox
                      checked={agreed}
                      onCheckedChange={(v) => setAgreed(v === true)}
                      className="mt-0.5"
                    />
                    <span className="text-sm leading-relaxed">
                      I have read and agree to the PROPAURA Privacy Policy. I consent to the processing of my
                      personal data for landlord account creation and rental-property management, and I accept the
                      responsibility and liability provisions in the Policy. I understand that my account cannot be
                      used until I accept this Policy.
                    </span>
                  </label>

                  <Button type="submit" className="w-full" disabled={loading}>
                    Accept and Continue
                  </Button>

                  <div className="flex items-center gap-2 justify-center text-xs text-muted-foreground">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    Acceptance is recorded with the version, time, IP address and device details.
                  </div>
                </form>
              </>
            )}
          </CardContent>
        </Card>
      </div>
      </div>
      {loading && <LoadingOverlay label="Recording acceptance…" />}
    </>
  );
}
