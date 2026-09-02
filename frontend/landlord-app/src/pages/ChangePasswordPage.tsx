import { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Eye, EyeOff, KeyRound, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { TotpSetupModal } from '@/components/modals/TotpSetupModal';
import { ROUTES } from '@/lib/routes';
import LoadingOverlay from '@shared/loading/LoadingOverlay';

interface PasswordRule {
  label: string;
  test: (pw: string) => boolean;
}

const PASSWORD_RULES: PasswordRule[] = [
  { label: 'At least 8 characters', test: (pw) => pw.length >= 8 },
  { label: 'Contains an uppercase letter', test: (pw) => /[A-Z]/.test(pw) },
  { label: 'Contains a lowercase letter', test: (pw) => /[a-z]/.test(pw) },
  { label: 'Contains a digit', test: (pw) => /\d/.test(pw) },
  { label: 'Contains a special character (!@#$%^&*_...)', test: (pw) => /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/.test(pw) },
  { label: 'No spaces', test: (pw) => !/\s/.test(pw) },
];

export default function ChangePasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const isGoogleSignup = searchParams.get('from') === 'google';
  const { changePassword, landlordUuid, hasTotp, username } = useAuth();
  const [form, setForm] = useState({ currentPassword: '', newPassword: '', confirmPassword: '' });
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [countdown, setCountdown] = useState(5);
  const [totpData, setTotpData] = useState<any>(null);
  const [showTotpModal, setShowTotpModal] = useState(false);

  const ruleResults = useMemo(
    () => PASSWORD_RULES.map((r) => ({ ...r, pass: r.test(form.newPassword) })),
    [form.newPassword],
  );
  const allRulesPass = ruleResults.every((r) => r.pass);
  const passwordsMatch = form.newPassword.length > 0 && form.confirmPassword.length > 0 && form.newPassword === form.confirmPassword;
  const canSubmit = allRulesPass && passwordsMatch && (!isGoogleSignup ? form.currentPassword.length > 0 : true);

  useEffect(() => {
    if (!success || !isGoogleSignup) return;
    if (countdown <= 0) {
      window.location.assign(ROUTES.LANDLORDPAGELOGIN);
      return;
    }
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown, success, isGoogleSignup]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!canSubmit) {
      setError('Please meet all password requirements.');
      return;
    }
    if (!isGoogleSignup && form.currentPassword === form.newPassword) {
      setError('New password must be different from current password.');
      return;
    }

    setLoading(true);
    try {
      const result = await changePassword(form.currentPassword, form.newPassword, form.confirmPassword);
      if (result.status === 'success') {
        if (isGoogleSignup) {
          try {
            await fetch(ROUTES.LANDLORDAPIAUTHLOGOUT, { method: 'POST', credentials: 'include' });
          } catch {
            // best-effort — full page reload to the login page resets client state anyway
          }
          setSuccess('Account created and password changed successfully!');
          setCountdown(5);
        } else if (result.next_step === 'totp_review' && result.totp) {
          setTotpData(result.totp);
          setShowTotpModal(true);
        } else {
          setSuccess('Password updated successfully! Redirecting...');
          setTimeout(() => {
            if (landlordUuid) {
              navigate(`/${landlordUuid}/dashboard`, { replace: true });
            } else {
              navigate('/dashboard', { replace: true });
            }
          }, 1500);
        }
      } else {
        setError(result.message || 'Failed to change password.');
      }
    } catch {
      setError('An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  const handleTotpClose = () => {
    setShowTotpModal(false);
    setSuccess('Password updated successfully! Redirecting...');
    setTimeout(() => {
      if (landlordUuid) {
        navigate(`/${landlordUuid}/dashboard`, { replace: true });
      } else {
        navigate('/dashboard', { replace: true });
      }
    }, 500);
  };

  const goToLogin = () => {
    window.location.assign(ROUTES.LANDLORDPAGELOGIN);
  };

  return (
    <>
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <div className="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-full">
              <KeyRound className="h-8 w-8 text-amber-600 dark:text-amber-400" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center">
            {isGoogleSignup ? 'Set Your Password' : 'Change Your Password'}
          </CardTitle>
          {username && (
            <p className="text-center text-sm font-medium text-muted-foreground">
              {username}
            </p>
          )}
          <CardDescription className="text-center">
            {isGoogleSignup
              ? 'Your account was created with Google. Set a password to finish creating your account.'
              : 'Your password has been reset by an administrator. Please set a new password to continue.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert className="mb-4 bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <AlertDescription className="text-green-800 dark:text-green-200">{success}</AlertDescription>
            </Alert>
          )}

          {success && isGoogleSignup && (
            <div className="space-y-3">
              <p className="text-sm text-center text-muted-foreground">
                Redirecting to login in {countdown}s...
              </p>
              <Button onClick={goToLogin} className="w-full">
                Login
              </Button>
            </div>
          )}

          {!(success && isGoogleSignup) && (
            <form onSubmit={handleSubmit} className="space-y-4">
              {!isGoogleSignup && (
                <div className="space-y-2">
                  <Label htmlFor="currentPassword">Current Password</Label>
                  <div className="relative">
                    <Input
                      id="currentPassword"
                      type={showCurrent ? 'text' : 'password'}
                      placeholder="Enter current password"
                      value={form.currentPassword}
                      onChange={(e) => setForm({ ...form, currentPassword: e.target.value })}
                      required
                      autoFocus
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrent(!showCurrent)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="newPassword">New Password</Label>
                <div className="relative">
                  <Input
                    id="newPassword"
                    type={showNew ? 'text' : 'password'}
                    placeholder="Enter new password (min 8 characters)"
                    value={form.newPassword}
                    onChange={(e) => setForm({ ...form, newPassword: e.target.value })}
                    required
                    minLength={8}
                    autoFocus={isGoogleSignup}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNew(!showNew)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {form.newPassword.length > 0 && (
                  <ul className="space-y-0.5 mt-1">
                    {ruleResults.map((r) => (
                      <li key={r.label} className="flex items-center gap-1.5 text-xs">
                        {r.pass ? (
                          <CheckCircle2 className="h-3 w-3 text-green-500 shrink-0" />
                        ) : (
                          <span className="h-3 w-3 rounded-full border border-muted-foreground/30 shrink-0" />
                        )}
                        <span className={r.pass ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}>
                          {r.label}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                <div className="relative">
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="Confirm new password"
                    value={form.confirmPassword}
                    onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                    required
                    minLength={8}
                  />
                  {form.confirmPassword.length > 0 && (
                    <span className="absolute right-3 top-1/2 -translate-y-1/2">
                      {passwordsMatch ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      ) : (
                        <span className="h-4 w-4 rounded-full border-2 border-red-400 block" />
                      )}
                    </span>
                  )}
                </div>
                {form.confirmPassword.length > 0 && !passwordsMatch && (
                  <p className="text-xs text-red-500">Passwords do not match.</p>
                )}
              </div>

              <Button type="submit" className="w-full" disabled={loading || !!success || !canSubmit}>
                {isGoogleSignup ? 'Set Password' : 'Update Password'}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>

      <TotpSetupModal
        isOpen={showTotpModal}
        onClose={handleTotpClose}
        totp={totpData}
        hasExistingTotp={hasTotp}
      />
      </div>
      {loading && <LoadingOverlay label="Updating…" />}
    </>
  );
}
