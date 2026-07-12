import { useState, useEffect } from 'react';
import { apiGet, apiPost } from '@/hooks/useApi';
import { ROUTES } from '@/lib/routes';
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
  const [totpData, setTotpData] = useState<TOTPData | null>(null);
  const [showRegenerateDialog, setShowRegenerateDialog] = useState(false);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [showSecret, setShowSecret] = useState(false);

  useEffect(() => {
    loadTOTPData();
  }, []);

  const loadTOTPData = async () => {
    try {
      const result: TOTPResponse = await apiGet(ROUTES.ADMIN_API_TOTP_QR);
      if (result.status === 'success') {
        setTotpData(result.totp);
      }
    } catch (err: any) {
      setError('Failed to load TOTP data: ' + err.message);
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
      const result: TOTPResponse = await apiPost(ROUTES.ADMIN_API_TOTP_REGENERATE, {
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
                Your TOTP secret is used for login verification and password recovery.
                Keep it secure and never share it with anyone.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {totpData ? (
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
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <QrCode className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Loading TOTP configuration...</p>
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
                Update your account password. You will need to use your TOTP code to verify the change.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                To change your password, please use the "Forgot Password" flow on the login page 
                with your TOTP verification code.
              </p>
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
    </div>
  );
}
