import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertTriangle, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ROUTES } from '@/lib/routes';
import MarkdownView from '@/components/privacy/MarkdownView';
import { BrandWave } from '@shared/loading/BrandWave';
import { Logo } from '@shared/brand/Logo';

interface PolicyInfo {
  version: string;
  effectiveDate: string;
  url: string;
  content: string;
}

export default function PrivacyPolicyPage() {
  const navigate = useNavigate();
  const [policy, setPolicy] = useState<PolicyInfo | null>(null);
  const [error, setError] = useState('');

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        <Card className="shadow-xl">
          <CardHeader className="space-y-1">
            <div className="flex items-center justify-center mb-4">
              <Logo height={36} />
            </div>
            <CardTitle className="text-2xl text-center">Privacy Policy</CardTitle>
            <CardDescription className="text-center">
              {policy
                ? `Version ${policy.version} — Effective ${policy.effectiveDate}`
                : 'Landlord Account Creation'}
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

            {policy?.content && <MarkdownView content={policy.content} />}

            <div className="mt-8 pt-6 border-t flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <ShieldCheck className="h-4 w-4 text-green-600" />
                Issued in compliance with the Digital Personal Data Protection Act, 2023
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => navigate(-1)}>Back</Button>
                <Link to={ROUTES.LANDLORDPAGESIGNUP}>
                  <Button>Return to Sign Up</Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
