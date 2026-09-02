import { useState, useEffect, useMemo } from 'react';
import { apiGet, apiPost } from '@/hooks/useApi';
import { ROUTES } from '@/lib/routes';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { 
  Shield, KeyRound, Copy, CheckCircle2, AlertTriangle, 
  RefreshCw, Eye, EyeOff, QrCode 
} from 'lucide-react';
import { BrandWave } from '@shared/loading/BrandWave';
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

interface TOTPData {
  secret: string;
  qr_code_base64: string;
  provisioning_uri: string;
}

interface TOTPResponse {
  status: string;
  totp: TOTPData;
}

export default function SecuritySettingsPage() {
  const { landlordUuid, hasTotp, totpEnabled, changePassword } = useAuth();
  const [totpData, setTotpData] = useState<TOTPData | null>(null);
  const [showRegenerateDialog, setShowRegenerateDialog] = useState(false);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [totpLoadError, setTotpLoadError] = useState('');

  // Password change form
  const [pwForm, setPwForm] = useState({ currentPassword: '', newPassword: '', confirmPassword: '' });
  const [showPwCurrent, setShowPwCurrent] = useState(false);
  const [showPwNew, setShowPwNew] = useState(false);
  const [pwLoading, setPwLoading] = useState(false);
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState('');
  const [totpModalData, setTotpModalData] = useState<any>(null);
  const [showTotpModal, setShowTotpModal] = useState(false);

  const ruleResults = useMemo(
    () => PASSWORD_RULES.map((r) => ({ ...r, pass: r.test(pwForm.newPassword) })),
    [pwForm.newPassword],
  );
  const allRulesPass = ruleResults.every((r) => r.pass);
  const passwordsMatch = pwForm.newPassword.length > 0 && pwForm.confirmPassword.length > 0 && pwForm.newPassword === pwForm.confirmPassword;
  const canPwSubmit = allRulesPass && passwordsMatch && pwForm.currentPassword.length > 0;

  useEffect(() => {
    if (landlordUuid && totpEnabled) {
      loadTOTPData();
    } else {
      setTotpData(null);
    }
  }, [landlordUuid, totpEnabled]);

  const loadTOTPData = async () => {
    setTotpLoadError('');
    try {
      const result: TOTPResponse = await apiGet(ROUTES.LANDLORDAPITOTPQR(landlordUuid!));
      if (result.status === 'success') {
        setTotpData(result.totp);
        if (!result.totp) {
          setTotpLoadError('TOTP secret not found. Please contact your administrator.');
        }
      } else {
        setTotpLoadError('Failed to load TOTP configuration.');
      }
    } catch (err: any) {
      setError('Failed to load TOTP data: ' + err.message);
      setTotpLoadError('Failed to load TOTP configuration. Please try again.');
    }
  };

  const copySecret = () => {
    if (totpData?.secret) {
      navigator.clipboard.writeText(totpData.secret);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    }
  };

  const handleRegenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result: TOTPResponse = await apiPost(ROUTES.LANDLORDAPITOTPREGENERATE(landlordUuid!), {
        password: password,
      });

      if (result.status === 'success') {
        setTotpData(result.totp);
        setSuccess('TOTP secret regenerated successfully!');
        setShowRegenerateDialog(false);
        setPassword('');
        setTimeout(() => setSuccess(''), 5000);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to regenerate TOTP');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError('');
    setPwSuccess('');

    if (pwForm.newPassword !== pwForm.confirmPassword) {
      setPwError('New passwords do not match.');
      return;
    }
    if (pwForm.newPassword.length < 8) {
      setPwError('Password must be at least 8 characters.');
      return;
    }
    if (pwForm.currentPassword === pwForm.newPassword) {
      setPwError('New password must be different from current password.');
      return;
    }

    setPwLoading(true);
    try {
      const result = await changePassword(pwForm.currentPassword, pwForm.newPassword, pwForm.confirmPassword);
      if (result.status === 'success') {
        if (result.next_step === 'totp_review' && result.totp) {
          setTotpModalData(result.totp);
          setShowTotpModal(true);
        } else {
          setPwSuccess('Password updated successfully!');
          setPwForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
          setTimeout(() => setPwSuccess(''), 5000);
        }
      } else {
        setPwError(result.message || 'Failed to change password.');
      }
    } catch {
      setPwError('An unexpected error occurred.');
    } finally {
      setPwLoading(false);
    }
  };

  return (
    <div className="container max-w-4xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3">
          <Shield className="h-8 w-8 text-primary" />
          Security Settings
        </h1>
        <p className="text-muted-foreground mt-2">
          Manage your account security and two-factor authentication
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {success && (
        <Alert className="mb-6 bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          <AlertDescription className="text-green-800 dark:text-green-200">{success}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="totp" className="space-y-6">
        <TabsList>
          <TabsTrigger value="totp" className="flex items-center gap-2">
            <QrCode className="h-4 w-4" />
            TOTP / 2FA
          </TabsTrigger>
          <TabsTrigger value="password" className="flex items-center gap-2">
            <KeyRound className="h-4 w-4" />
            Password
          </TabsTrigger>
        </TabsList>

        <TabsContent value="totp" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <QrCode className="h-5 w-5" />
                Two-Factor Authentication (TOTP)
              </CardTitle>
              <CardDescription>
                {totpEnabled
                  ? "Your TOTP secret is used for login verification and password recovery. Keep it secure and never share it with anyone."
                  : "Two-factor authentication adds an extra layer of security to your account."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {!totpEnabled ? (
                <div className="text-center py-8">
                  <QrCode className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <p className="text-muted-foreground font-medium">
                    {hasTotp ? "Two-Factor Authentication is disabled" : "Two-Factor Authentication is not configured"}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {hasTotp
                      ? "Enable TOTP from Settings to require a verification code after your password for login."
                      : "Contact your administrator to enable TOTP for your account."}
                  </p>
                </div>
              ) : totpData ? (
                <>
                  <div className="flex flex-col items-center space-y-4">
                    <div className="p-4 bg-white rounded-xl border-2 border-dashed border-muted">
                      <img
                        src={`data:image/png;base64,${totpData.qr_code_base64}`}
                        alt="TOTP QR Code"
                        className="w-56 h-56"
                      />
                    </div>
                    <p className="text-sm text-muted-foreground text-center">
                      Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
                    </p>
                  </div>

                  <Separator />

                  <div className="space-y-3">
                    <Label>TOTP Secret (Manual Entry)</Label>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Input
                          value={showSecret ? totpData.secret : '•'.repeat(totpData.secret.length)}
                          readOnly
                          className="font-mono text-sm pr-10"
                        />
                        <button
                          type="button"
                          onClick={() => setShowSecret(!showSecret)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        >
                          {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      </div>
                      <Button variant="outline" size="icon" onClick={copySecret}>
                        {copiedSecret ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>

                  <Separator />

                  <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5" />
                      <div>
                        <h4 className="font-medium text-amber-800 dark:text-amber-200">Important Security Notice</h4>
                        <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
                          If you regenerate your TOTP secret, your old authenticator codes will stop working immediately. 
                          Make sure to update all your devices before proceeding.
                        </p>
                      </div>
                    </div>
                  </div>

                  <Button
                    variant="destructive"
                    className="w-full"
                    onClick={() => {
                      setShowRegenerateDialog(true);
                      setError('');
                    }}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Regenerate TOTP Secret
                  </Button>
                </>
              ) : totpLoadError ? (
                <div className="text-center py-8 space-y-3">
                  <AlertTriangle className="h-12 w-12 mx-auto text-muted-foreground opacity-50" />
                  <p className="text-muted-foreground font-medium">{totpLoadError}</p>
                  <Button variant="outline" size="sm" onClick={loadTOTPData}>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Retry
                  </Button>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <QrCode className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <BrandWave stacked label="Loading TOTP configuration…" />
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="password" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <KeyRound className="h-5 w-5" />
                Change Password
              </CardTitle>
              <CardDescription>
                Update your account password. Use a strong, unique password.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {pwError && (
                <Alert variant="destructive" className="mb-4">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{pwError}</AlertDescription>
                </Alert>
              )}
              {pwSuccess && (
                <Alert className="mb-4 bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  <AlertDescription className="text-green-800 dark:text-green-200">{pwSuccess}</AlertDescription>
                </Alert>
              )}
              <form onSubmit={handlePasswordChange} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="sec-currentPassword">Current Password</Label>
                  <div className="relative">
                    <Input
                      id="sec-currentPassword"
                      type={showPwCurrent ? 'text' : 'password'}
                      placeholder="Enter current password"
                      value={pwForm.currentPassword}
                      onChange={(e) => setPwForm({ ...pwForm, currentPassword: e.target.value })}
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPwCurrent(!showPwCurrent)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showPwCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sec-newPassword">New Password</Label>
                  <div className="relative">
                    <Input
                      id="sec-newPassword"
                      type={showPwNew ? 'text' : 'password'}
                      placeholder="Enter new password (min 8 characters)"
                      value={pwForm.newPassword}
                      onChange={(e) => setPwForm({ ...pwForm, newPassword: e.target.value })}
                      required
                      minLength={8}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPwNew(!showPwNew)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showPwNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {pwForm.newPassword.length > 0 && (
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
                  <Label htmlFor="sec-confirmPassword">Confirm New Password</Label>
                  <div className="relative">
                    <Input
                      id="sec-confirmPassword"
                      type="password"
                      placeholder="Confirm new password"
                      value={pwForm.confirmPassword}
                      onChange={(e) => setPwForm({ ...pwForm, confirmPassword: e.target.value })}
                      required
                      minLength={8}
                    />
                    {pwForm.confirmPassword.length > 0 && (
                      <span className="absolute right-3 top-1/2 -translate-y-1/2">
                        {passwordsMatch ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : (
                          <span className="h-4 w-4 rounded-full border-2 border-red-400 block" />
                        )}
                      </span>
                    )}
                  </div>
                  {pwForm.confirmPassword.length > 0 && !passwordsMatch && (
                    <p className="text-xs text-red-500">Passwords do not match.</p>
                  )}
                </div>
                <Button type="submit" className="w-full" disabled={pwLoading || !canPwSubmit}>
                  {pwLoading ? 'Updating...' : 'Update Password'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Regenerate TOTP Dialog */}
      <Dialog open={showRegenerateDialog} onOpenChange={setShowRegenerateDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              Regenerate TOTP Secret
            </DialogTitle>
            <DialogDescription>
              This will invalidate your current TOTP codes. Enter your password to confirm.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleRegenerate} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="confirm-password">Current Password</Label>
              <div className="relative">
                <Input
                  id="confirm-password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your current password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="flex gap-3">
              <Button
                type="button"
                variant="outline"
                className="flex-1"
                onClick={() => {
                  setShowRegenerateDialog(false);
                  setPassword('');
                  setError('');
                }}
              >
                Cancel
              </Button>
              <Button type="submit" variant="destructive" className="flex-1" disabled={loading}>
                {loading ? 'Regenerating...' : 'Confirm Regenerate'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <TotpSetupModal
        isOpen={showTotpModal}
        onClose={() => {
          setShowTotpModal(false);
          setPwSuccess('Password updated successfully!');
          setPwForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
          setTimeout(() => setPwSuccess(''), 5000);
        }}
        totp={totpModalData}
        hasExistingTotp={totpEnabled}
      />
    </div>
  );
}
