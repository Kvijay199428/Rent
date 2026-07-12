import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPost, apiGet } from '@/hooks/useApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Eye, EyeOff, Shield, AlertTriangle, ArrowLeft, KeyRound } from 'lucide-react';
import { ROUTES } from '@/lib/routes';

interface LoginResponse {
  status: string;
  message?: string;
  username?: string;
  admin_id?: number;
}

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [loginData, setLoginData] = useState({ username: '', password: '', totpToken: '', rememberMe: false });
  const [forgotData, setForgotData] = useState({ username: '', totpToken: '', newPassword: '', confirmPassword: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [needsTOTP, setNeedsTOTP] = useState(false);
  const [showForgotDialog, setShowForgotDialog] = useState(false);
  const [forgotStep, setForgotStep] = useState<'verify' | 'reset'>('verify');
  const [setupRequired, setSetupRequired] = useState(false);

  useEffect(() => {
    apiGet(ROUTES.ADMIN_API_SETUP_REQUIRED)
      .then((data: any) => {
        if (data.setup_required) {
          setSetupRequired(true);
          navigate('/setup');
        }
      })
      .catch(() => {});
  }, [navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (needsTOTP) {
        // Step 2: Login with TOTP
        const result = await apiPost(ROUTES.ADMIN_API_AUTH_LOGIN_TOTP, {
          username: loginData.username,
          password: loginData.password,
          totp_token: loginData.totpToken,
          remember_me: loginData.rememberMe,
        });

        if (result.status === 'success') {
          navigate('/');
        }
      } else {
        // Step 1: Initial login attempt
        const result: LoginResponse = await apiPost(ROUTES.ADMIN_API_AUTH_LOGIN, {
          username: loginData.username,
          password: loginData.password,
          remember_me: loginData.rememberMe,
        });

        if (result.status === 'totp_required') {
          setNeedsTOTP(true);
        } else if (result.status === 'success') {
          navigate('/');
        }
      }
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (forgotStep === 'verify') {
        const result = await apiPost(ROUTES.ADMIN_API_PASSWORD_FORGOT_VERIFY, {
          username: forgotData.username,
          totp_token: forgotData.totpToken,
        });

        if (result.status === 'success') {
          setForgotStep('reset');
          setSuccess('TOTP verified. Enter your new password.');
        }
      } else {
        if (forgotData.newPassword !== forgotData.confirmPassword) {
          setError('Passwords do not match');
          setLoading(false);
          return;
        }

        if (forgotData.newPassword.length < 6) {
          setError('Password must be at least 6 characters');
          setLoading(false);
          return;
        }

        const result = await apiPost(ROUTES.ADMIN_API_PASSWORD_FORGOT_RESET, {
          username: forgotData.username,
          totp_token: forgotData.totpToken,
          new_password: forgotData.newPassword,
          confirm_password: forgotData.confirmPassword,
        });

        if (result.status === 'success') {
          setSuccess('Password reset successfully! Redirecting to login...');
          setTimeout(() => {
            setShowForgotDialog(false);
            setForgotStep('verify');
            setForgotData({ username: '', totpToken: '', newPassword: '', confirmPassword: '' });
            setSuccess('');
          }, 2000);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Operation failed');
    } finally {
      setLoading(false);
    }
  };

  if (setupRequired) {
    return null; // Will redirect
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <div className="p-3 bg-primary/10 rounded-full">
              <Shield className="h-8 w-8 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center">Admin Login</CardTitle>
          <CardDescription className="text-center">
            Enter your credentials to access the dashboard
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                placeholder="Enter username"
                value={loginData.username}
                onChange={(e) => {
                  setLoginData({ ...loginData, username: e.target.value });
                  setNeedsTOTP(false);
                  setError('');
                }}
                required
                disabled={needsTOTP}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter password"
                  value={loginData.password}
                  onChange={(e) => {
                    setLoginData({ ...loginData, password: e.target.value });
                    setNeedsTOTP(false);
                    setError('');
                  }}
                  required
                  disabled={needsTOTP}
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

            {needsTOTP && (
              <div className="space-y-2 animate-in fade-in slide-in-from-top-2">
                <Label htmlFor="totp" className="flex items-center gap-2">
                  <KeyRound className="h-4 w-4" />
                  TOTP Code
                </Label>
                <Input
                  id="totp"
                  placeholder="Enter 6-digit code from authenticator"
                  value={loginData.totpToken}
                  onChange={(e) => setLoginData({ ...loginData, totpToken: e.target.value })}
                  required
                  maxLength={6}
                  pattern="\d{6}"
                  className="font-mono text-lg tracking-widest"
                  autoFocus
                />
                <p className="text-xs text-muted-foreground">
                  Open your authenticator app and enter the 6-digit code
                </p>
              </div>
            )}

            <div className="flex items-center justify-between">
              <label className="flex items-center space-x-2 text-sm">
                <input
                  type="checkbox"
                  checked={loginData.rememberMe}
                  onChange={(e) => setLoginData({ ...loginData, rememberMe: e.target.checked })}
                  className="rounded border-gray-300"
                />
                <span>Remember me</span>
              </label>
              <button
                type="button"
                onClick={() => {
                  setShowForgotDialog(true);
                  setForgotStep('verify');
                  setError('');
                  setSuccess('');
                }}
                className="text-sm text-primary hover:underline"
              >
                Forgot password?
              </button>
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Please wait...' : needsTOTP ? 'Verify & Login' : 'Login'}
            </Button>

            {needsTOTP && (
              <Button
                type="button"
                variant="ghost"
                className="w-full"
                onClick={() => {
                  setNeedsTOTP(false);
                  setLoginData({ ...loginData, totpToken: '' });
                }}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to password
              </Button>
            )}
          </form>
        </CardContent>
      </Card>

      {/* Forgot Password Dialog */}
      <Dialog open={showForgotDialog} onOpenChange={setShowForgotDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Reset Password</DialogTitle>
            <DialogDescription>
              {forgotStep === 'verify' 
                ? 'Enter your username and TOTP code to verify your identity.'
                : 'Create a new password for your account.'}
            </DialogDescription>
          </DialogHeader>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert className="mb-4 bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800">
              <AlertDescription className="text-green-800 dark:text-green-200">{success}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleForgotPassword} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="forgot-username">Username</Label>
              <Input
                id="forgot-username"
                placeholder="Enter your username"
                value={forgotData.username}
                onChange={(e) => setForgotData({ ...forgotData, username: e.target.value })}
                required
                disabled={forgotStep === 'reset'}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="forgot-totp" className="flex items-center gap-2">
                <KeyRound className="h-4 w-4" />
                TOTP Code
              </Label>
              <Input
                id="forgot-totp"
                placeholder="6-digit code from authenticator"
                value={forgotData.totpToken}
                onChange={(e) => setForgotData({ ...forgotData, totpToken: e.target.value })}
                required
                maxLength={6}
                pattern="\d{6}"
                className="font-mono tracking-widest"
                disabled={forgotStep === 'reset'}
              />
            </div>

            {forgotStep === 'reset' && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="new-password">New Password</Label>
                  <div className="relative">
                    <Input
                      id="new-password"
                      type={showNewPassword ? 'text' : 'password'}
                      placeholder="Minimum 6 characters"
                      value={forgotData.newPassword}
                      onChange={(e) => setForgotData({ ...forgotData, newPassword: e.target.value })}
                      required
                      minLength={6}
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirm-password">Confirm New Password</Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    placeholder="Confirm your new password"
                    value={forgotData.confirmPassword}
                    onChange={(e) => setForgotData({ ...forgotData, confirmPassword: e.target.value })}
                    required
                  />
                </div>
              </>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading 
                ? 'Please wait...' 
                : forgotStep === 'verify' 
                  ? 'Verify TOTP' 
                  : 'Reset Password'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
