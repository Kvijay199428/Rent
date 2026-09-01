import { useState } from 'react';
import { Shield, User, KeyRound, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { useAuth } from '@/contexts/AuthContext';
import { APP_BASE } from '@/lib/runtime';
import { ROUTES } from '@/lib/routes';
import AuthLayout from '@/components/layout/AuthLayout';
import LoadingOverlay from '@shared/loading/LoadingOverlay';
import { Logo } from '@shared/brand/Logo';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const { login, isLoading } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!username.trim() || !password.trim()) {
      setError('Please enter both username and password');
      return;
    }

    const success = await login(username, password, rememberMe);
    if (success) {
      window.location.assign(APP_BASE || '/');
    } else {
      setError('Invalid username or password');
    }
  };

  return (
    <>
      <AuthLayout>
      <div className="w-full max-w-sm">
        <div className="bg-card border rounded-xl shadow-lg p-6">
          {/* Logo */}
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-primary/10 text-primary mb-3">
              <Shield size={28} />
            </div>
            <h3 className="text-xl font-bold">System Admin</h3>
          </div>

          {/* Error */}
          {error && (
            <div className="mb-4 p-2.5 rounded-lg bg-red-50 text-red-600 text-sm text-center dark:bg-red-900/20">
              {error}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-muted-foreground text-sm">
                Username
              </Label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-9"
                  placeholder="admin"
                  autoFocus
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-muted-foreground text-sm">
                Password
              </Label>
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9"
                  placeholder="••••••"
                  required
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="remember"
                checked={rememberMe}
                onCheckedChange={(v) => setRememberMe(!!v)}
              />
              <Label htmlFor="remember" className="text-sm text-muted-foreground cursor-pointer">
                Keep me logged in
              </Label>
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={isLoading}
            >
              {'Login to Dashboard'}
            </Button>
          </form>
        </div>

        <div className="text-center mt-4">
          <span className="text-xs text-muted-foreground inline-flex items-center gap-1"><Logo height={12} /> v3.0.0</span>
        </div>
      </div>
      </AuthLayout>
      {isLoading && <LoadingOverlay label="Logging in…" />}
    </>
  );
}
