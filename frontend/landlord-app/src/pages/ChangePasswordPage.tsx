import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Eye, EyeOff, KeyRound, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { TotpSetupModal } from '@/components/modals/TotpSetupModal';

export default function ChangePasswordPage() {
  const navigate = useNavigate();
  const { changePassword, landlordUuid, hasTotp } = useAuth();
  const [form, setForm] = useState({ currentPassword: '', newPassword: '', confirmPassword: '' });
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [totpData, setTotpData] = useState<any>(null);
  const [showTotpModal, setShowTotpModal] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (form.newPassword !== form.confirmPassword) {
      setError('New passwords do not match.');
      return;
    }
    if (form.newPassword.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    if (form.currentPassword === form.newPassword) {
      setError('New password must be different from current password.');
      return;
    }

    setLoading(true);
    try {
      const result = await changePassword(form.currentPassword, form.newPassword, form.confirmPassword);
      if (result.status === 'success') {
        if (result.next_step === 'totp_review' && result.totp) {
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

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <div className="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-full">
              <KeyRound className="h-8 w-8 text-amber-600 dark:text-amber-400" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center">Change Your Password</CardTitle>
          <CardDescription className="text-center">
            Your password has been reset by an administrator. Please set a new password to continue.
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

          <form onSubmit={handleSubmit} className="space-y-4">
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

            <div className="space-y-2">
              <Label htmlFor="newPassword">New Password</Label>
              <div className="relative">
                <Input
                  id="newPassword"
                  type={showNew ? 'text' : 'password'}
                  placeholder="Enter new password (min 6 characters)"
                  value={form.newPassword}
                  onChange={(e) => setForm({ ...form, newPassword: e.target.value })}
                  required
                  minLength={6}
                />
                <button
                  type="button"
                  onClick={() => setShowNew(!showNew)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm New Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Confirm new password"
                value={form.confirmPassword}
                onChange={(e) => setForm({ ...form, confirmPassword: e.target.value })}
                required
                minLength={6}
              />
            </div>

            <Button type="submit" className="w-full" disabled={loading || !!success}>
              {loading ? 'Updating...' : 'Update Password'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <TotpSetupModal
        isOpen={showTotpModal}
        onClose={handleTotpClose}
        totp={totpData}
        hasExistingTotp={hasTotp}
      />
    </div>
  );
}
