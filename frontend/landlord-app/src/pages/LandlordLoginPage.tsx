import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Eye, EyeOff, Shield, AlertTriangle, ArrowLeft, KeyRound } from 'lucide-react';
import AuthLayout from '@/components/layout/AuthLayout';
import LoadingOverlay from '@shared/loading/LoadingOverlay';

export default function LandlordLoginPage() {
  const navigate = useNavigate();
  const { login, verifyTotp, isAuthenticated, isLoading, landlordUuid, googleLogin } = useAuth();
  const [loginData, setLoginData] = useState({ username: '', password: '', totpToken: '', rememberMe: false });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [needsTOTP, setNeedsTOTP] = useState(false);

  // Auth guard: redirect to dashboard if already authenticated
  useEffect(() => {
    if (!isLoading && isAuthenticated && landlordUuid) {
      navigate(`/${landlordUuid}/dashboard`, { replace: true });
    }
  }, [isLoading, isAuthenticated, landlordUuid, navigate]);

  const handleGoogleSuccess = async (credentialResponse: any) => {
    setError("");
    setLoading(true);
    try {
      const result = await googleLogin(credentialResponse.credential, loginData.rememberMe);
      if (result.status === "failed") {
        setError(result.message || "Google authentication failed");
        return;
      }
      if (result.status === "password_change_required") {
        navigate("/change-password?from=google", { replace: true });
        return;
      }
      if (result.status === "success") {
        navigate(`/${result.landlordUuid}/dashboard`, { replace: true });
      }
    } catch {
      setError("Network error during Google authentication");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (needsTOTP) {
        const result = await verifyTotp(
          loginData.username,
          loginData.password,
          loginData.totpToken,
          loginData.rememberMe,
        );

        if (result && result.status === "password_change_required") {
          navigate("/change-password", { replace: true });
          return;
        }

        if (!result || result.status !== "success") {
          setError("Invalid TOTP code. Please try again.");
          return;
        }

        return;
      }

      const result = await login(
        loginData.username,
        loginData.password,
        loginData.rememberMe,
      );

      if (result.status === "totp_required") {
        setNeedsTOTP(true);
        return;
      }

      if (result.status === "password_change_required") {
        navigate("/change-password", { replace: true });
        return;
      }

      if (result.status === "success") {
        navigate(`/${result.landlordUuid}/dashboard`, { replace: true });
        return;
      }

      setError("Invalid username or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <AuthLayout>
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <div className="p-3 bg-primary/10 rounded-full">
              <Shield className="h-8 w-8 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center">Landlord Login</CardTitle>
          <CardDescription className="text-center">
            Enter your credentials to manage your properties
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
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {needsTOTP ? 'Verify & Login' : 'Login'}
            </Button>

            {!needsTOTP && (
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">Or continue with</span>
                </div>
              </div>
            )}

            {!needsTOTP && (
              <div className="flex justify-center">
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={() => setError("Google Sign-In failed")}
                  size="large"
                  width={384}
                />
              </div>
            )}

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
        <CardFooter className="flex justify-center border-t p-4 mt-2">
          <p className="text-sm text-muted-foreground">
            Don't have an account? <Link to="/signup" className="text-primary hover:underline font-medium">Sign up</Link>
          </p>
        </CardFooter>
      </Card>
      </AuthLayout>
      {loading && <LoadingOverlay label={needsTOTP ? "Verifying…" : "Signing in…"} />}
    </>
  );
}
