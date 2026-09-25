import { useState, useMemo } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Eye, EyeOff, CheckCircle2, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { TotpSetupModal } from '@/components/modals/TotpSetupModal';

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

interface ChangePasswordDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ChangePasswordDialog({ open, onOpenChange }: ChangePasswordDialogProps) {
  const { changePassword, totpEnabled } = useAuth();
  const [form, setForm] = useState({ currentPassword: '', newPassword: '', confirmPassword: '', totpToken: '' });
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showTotp, setShowTotp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [totpData, setTotpData] = useState<any>(null);
  const [showTotpModal, setShowTotpModal] = useState(false);

  const ruleResults = useMemo(
    () => PASSWORD_RULES.map((r) => ({ ...r, pass: r.test(form.newPassword) })),
    [form.newPassword],
  );
  const allRulesPass = ruleResults.every((r) => r.pass);
  const passwordsMatch =
    form.newPassword.length > 0 &&
    form.confirmPassword.length > 0 &&
    form.newPassword === form.confirmPassword;
  const canSubmit =
    allRulesPass && passwordsMatch && form.currentPassword.length > 0 && (!totpEnabled || form.totpToken.length > 0);

  const reset = () => {
    setForm({ currentPassword: '', newPassword: '', confirmPassword: '', totpToken: '' });
    setShowCurrent(false);
    setShowNew(false);
    setShowTotp(false);
    setError('');
    setSuccess('');
    setTotpData(null);
    setShowTotpModal(false);
  };

  const handleClose = (nextOpen: boolean) => {
    if (!nextOpen && !loading) reset();
    onOpenChange(nextOpen);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!allRulesPass || !passwordsMatch) {
      setError('Please meet all password requirements.');
      return;
    }
    if (form.currentPassword === form.newPassword) {
      setError('New password must be different from current password.');
      return;
    }
    if (totpEnabled && !form.totpToken) {
      setError('Enter your TOTP code to confirm the password change.');
      return;
    }

    setLoading(true);
    try {
      const result = await changePassword(
        form.currentPassword,
        form.newPassword,
        form.confirmPassword,
        totpEnabled ? form.totpToken : undefined,
      );
      if (result.status === 'success') {
        if (result.next_step === 'totp_review' && result.totp) {
          setTotpData(result.totp);
          setShowTotpModal(true);
        } else {
          setSuccess('Password updated successfully!');
          setTimeout(() => handleClose(false), 1500);
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
    setSuccess('Password updated successfully!');
    setTimeout(() => handleClose(false), 1500);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Change Password</DialogTitle>
            <DialogDescription>
              Update your login password. {totpEnabled && 'Enter your TOTP code to confirm the change.'}
            </DialogDescription>
          </DialogHeader>

          {success ? (
            <Alert className="mb-2 bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <AlertDescription className="text-green-800 dark:text-green-200">{success}</AlertDescription>
            </Alert>
          ) : (
            <>
              {error && (
                <Alert variant="destructive" className="mb-2">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="cp-currentPassword">Current Password</Label>
                  <div className="relative">
                    <Input
                      id="cp-currentPassword"
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
                      tabIndex={-1}
                    >
                      {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="cp-newPassword">New Password</Label>
                  <div className="relative">
                    <Input
                      id="cp-newPassword"
                      type={showNew ? 'text' : 'password'}
                      placeholder="Enter new password (min 8 characters)"
                      value={form.newPassword}
                      onChange={(e) => setForm({ ...form, newPassword: e.target.value })}
                      required
                      minLength={8}
                    />
                    <button
                      type="button"
                      onClick={() => setShowNew(!showNew)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      tabIndex={-1}
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
                  <Label htmlFor="cp-confirmPassword">Confirm New Password</Label>
                  <div className="relative">
                    <Input
                      id="cp-confirmPassword"
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

                {totpEnabled && (
                  <div className="space-y-2">
                    <Label htmlFor="cp-totpToken">TOTP Code</Label>
                    <div className="relative">
                      <Input
                        id="cp-totpToken"
                        type={showTotp ? 'text' : 'password'}
                        placeholder="Enter 6-digit TOTP code"
                        value={form.totpToken}
                        onChange={(e) => setForm({ ...form, totpToken: e.target.value.replace(/\D/g, '').slice(0, 6) })}
                        required
                        inputMode="numeric"
                        autoComplete="one-time-code"
                      />
                      <button
                        type="button"
                        onClick={() => setShowTotp(!showTotp)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        tabIndex={-1}
                      >
                        {showTotp ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                )}

                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => handleClose(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={loading || !canSubmit}>
                    {loading ? 'Updating…' : 'Update Password'}
                  </Button>
                </DialogFooter>
              </form>
            </>
          )}
        </DialogContent>
      </Dialog>

      <TotpSetupModal
        isOpen={showTotpModal}
        onClose={handleTotpClose}
        totp={totpData}
        hasExistingTotp={totpEnabled}
      />
    </>
  );
}