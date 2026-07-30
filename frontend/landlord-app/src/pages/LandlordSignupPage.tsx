import { useState, useRef, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Eye, EyeOff, Shield, AlertTriangle, Check, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import AuthLayout from '@/components/layout/AuthLayout';
import { ROUTES } from '@/lib/routes';

type FieldStatus = 'idle' | 'checking' | 'available' | 'taken' | 'error';

interface Conflict {
  field: string;
  code: string;
  message: string;
  suggestions?: string[];
}

export default function LandlordSignupPage() {
  const navigate = useNavigate();
  const [signupData, setSignupData] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    fullName: '',
    email: '',
    phone: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [usernameStatus, setUsernameStatus] = useState<FieldStatus>('idle');
  const [emailStatus, setEmailStatus] = useState<FieldStatus>('idle');
  const [usernameSuggestions, setUsernameSuggestions] = useState<string[]>([]);
  const [passwordStrength, setPasswordStrength] = useState(0);
  const [googleLoading, setGoogleLoading] = useState(false);

  const usernameTimer = useRef<ReturnType<typeof setTimeout>>();
  const emailTimer = useRef<ReturnType<typeof setTimeout>>();

  const checkUsername = useCallback((value: string) => {
    if (usernameTimer.current) clearTimeout(usernameTimer.current);
    if (value.length < 3) {
      setUsernameStatus('idle');
      setUsernameSuggestions([]);
      return;
    }
    setUsernameStatus('checking');
    usernameTimer.current = setTimeout(async () => {
      try {
        const res = await fetch(`${ROUTES.LANDLORDAPIAUTHCHECKUSERNAME}?username=${encodeURIComponent(value)}`);
        const data = await res.json();
        if (data.available) {
          setUsernameStatus('available');
          setUsernameSuggestions([]);
        } else {
          setUsernameStatus('taken');
          setUsernameSuggestions(data.suggestions || []);
        }
      } catch {
        setUsernameStatus('error');
      }
    }, 400);
  }, []);

  const checkEmail = useCallback((value: string) => {
    if (emailTimer.current) clearTimeout(emailTimer.current);
    if (!value.includes('@') || value.length < 5) {
      setEmailStatus('idle');
      return;
    }
    setEmailStatus('checking');
    emailTimer.current = setTimeout(async () => {
      try {
        const res = await fetch(`${ROUTES.LANDLORDAPIAUTHCHECKEMAIL}?email=${encodeURIComponent(value)}`);
        const data = await res.json();
        setEmailStatus(data.available ? 'available' : 'taken');
        if (!data.available) {
          toast.error('Email is already registered', { description: 'Please use a different email or log in.' });
        }
      } catch {
        setEmailStatus('error');
      }
    }, 500);
  }, []);

  const calcPasswordStrength = (pw: string): number => {
    let s = 0;
    if (pw.length >= 8) s++;
    if (pw.length >= 12) s++;
    if (/[A-Z]/.test(pw)) s++;
    if (/[0-9]/.test(pw)) s++;
    if (/[^A-Za-z0-9]/.test(pw)) s++;
    return s;
  };

  const handleChange = (field: string, value: string) => {
    setSignupData(prev => ({ ...prev, [field]: value }));
    setError('');

    if (field === 'username') {
      const clean = value.toLowerCase().replace(/[^a-z0-9_]/g, '');
      if (clean !== value) setSignupData(prev => ({ ...prev, username: clean }));
      checkUsername(clean);
    }
    if (field === 'email') checkEmail(value);
    if (field === 'password') setPasswordStrength(calcPasswordStrength(value));
  };

  const selectSuggestion = (s: string) => {
    setSignupData(prev => ({ ...prev, username: s }));
    setUsernameStatus('available');
    setUsernameSuggestions([]);
    toast.success(`Username "${s}" is available`);
  };

  const handleGoogleSuccess = async (credentialResponse: any) => {
    setError('');
    setGoogleLoading(true);
    try {
      const res = await fetch(ROUTES.LANDLORDAPIAUTHGOOGLE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: credentialResponse.credential, rememberMe: false }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Google Sign-Up failed");
        return;
      }
      if (data.status === "success") {
        toast.success('Account created via Google!', { description: 'Redirecting...' });
        setTimeout(() => navigate(`/${data.landlord.landlordUuid}/dashboard`, { replace: true }), 1200);
      }
    } catch {
      setError("Network error during Google Sign-Up");
    } finally {
      setGoogleLoading(false);
    }
  };

  const handleSignup = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');

    if (signupData.password !== signupData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (signupData.username.length < 3) {
      setError('Username must be at least 3 characters.');
      return;
    }
    if (signupData.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(ROUTES.LANDLORDAPIAUTHSIGNUP, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signupData),
      });
      const data = await response.json();

      if (!response.ok) {
        if (data.detail?.conflicts) {
          const conflicts: Conflict[] = data.detail.conflicts;
          conflicts.forEach(c => {
            toast.error(c.message, { description: c.suggestions ? `Try: ${c.suggestions.slice(0, 3).join(', ')}` : undefined, duration: 6000 });
            if (c.field === 'username') setUsernameStatus('taken');
            if (c.field === 'email') setEmailStatus('taken');
          });
          setError(data.detail.message || 'Some fields need attention.');
        } else if (typeof data.detail === 'string') {
          setError(data.detail);
        } else {
          setError('Signup failed. Please check your information.');
        }
        return;
      }

      if (data.status === 'success') {
        toast.success('Account created!', { description: 'Redirecting to login...' });
        setTimeout(() => navigate('/login', { replace: true }), 1200);
        return;
      }
      setError('An unexpected error occurred.');
    } catch {
      setError('Network error. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const fieldIcon = (status: FieldStatus) => {
    if (status === 'checking') return <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />;
    if (status === 'available') return <Check className="h-4 w-4 text-green-500" />;
    if (status === 'taken' || status === 'error') return <X className="h-4 w-4 text-red-500" />;
    return null;
  };

  const fieldBorder = (status: FieldStatus) => {
    if (status === 'available') return 'border-green-500 focus-visible:ring-green-500';
    if (status === 'taken' || status === 'error') return 'border-red-500 focus-visible:ring-red-500';
    return '';
  };

  const strengthColor = (s: number) => s <= 2 ? 'bg-red-400' : s <= 3 ? 'bg-yellow-400' : 'bg-green-500';
  const strengthLabel = (s: number) => s <= 1 ? 'Very weak' : s <= 2 ? 'Weak' : s <= 3 ? 'Fair' : s <= 4 ? 'Good' : 'Strong';

  return (
    <AuthLayout>
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-4">
            <div className="p-3 bg-primary/10 rounded-full">
              <Shield className="h-8 w-8 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl text-center">Landlord Signup</CardTitle>
          <CardDescription className="text-center">
            Create an account to manage your properties
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSignup} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="fullName">Full Name</Label>
              <Input
                id="fullName"
                placeholder="Enter full name"
                value={signupData.fullName}
                onChange={e => handleChange('fullName', e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">
                Email Address
                {emailStatus === 'available' && <span className="ml-2 text-xs text-green-500">Available</span>}
              </Label>
              <div className="relative">
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter email address"
                  value={signupData.email}
                  onChange={e => handleChange('email', e.target.value)}
                  className={fieldBorder(emailStatus)}
                  required
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">{fieldIcon(emailStatus)}</span>
              </div>
              {emailStatus === 'taken' && (
                <p className="text-xs text-red-500">This email is already registered.</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="username">
                Username
                {usernameStatus === 'available' && <span className="ml-2 text-xs text-green-500">Available</span>}
              </Label>
              <div className="relative">
                <Input
                  id="username"
                  placeholder="letters, numbers, underscores"
                  value={signupData.username}
                  onChange={e => handleChange('username', e.target.value)}
                  className={fieldBorder(usernameStatus)}
                  required
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2">{fieldIcon(usernameStatus)}</span>
              </div>
              {usernameSuggestions.length > 0 && (
                <div className="p-3 bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800 rounded-md">
                  <p className="text-sm text-orange-700 dark:text-orange-300 font-medium mb-2">
                    "{signupData.username}" is taken. Try one of these:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {usernameSuggestions.map(s => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => selectSuggestion(s)}
                        className="px-3 py-1 bg-white dark:bg-orange-900 border border-orange-300 dark:border-orange-700 rounded-full text-sm text-orange-700 dark:text-orange-200 hover:bg-orange-100 dark:hover:bg-orange-800 transition-colors"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="phone">Phone (optional)</Label>
              <Input
                id="phone"
                type="tel"
                placeholder="10-digit mobile number"
                value={signupData.phone}
                onChange={e => handleChange('phone', e.target.value.replace(/\D/g, ''))}
                maxLength={10}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">
                Password
                {signupData.password.length > 0 && signupData.password.length < 8 && (
                  <span className="ml-2 text-xs text-red-500">Min 8 characters</span>
                )}
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter password"
                  value={signupData.password}
                  onChange={e => handleChange('password', e.target.value)}
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
              {signupData.password.length > 0 && (
                <div className="space-y-1">
                  <div className="flex gap-1 h-1.5">
                    {[1, 2, 3, 4, 5].map(level => (
                      <div
                        key={level}
                        className={`flex-1 rounded-full transition-colors ${level <= passwordStrength ? strengthColor(passwordStrength) : 'bg-gray-200 dark:bg-gray-700'}`}
                      />
                    ))}
                  </div>
                  <p className="text-xs text-muted-foreground">{strengthLabel(passwordStrength)}</p>
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Confirm password"
                  value={signupData.confirmPassword}
                  onChange={e => handleChange('confirmPassword', e.target.value)}
                  className={
                    signupData.confirmPassword && signupData.password !== signupData.confirmPassword
                      ? 'border-red-500 focus-visible:ring-red-500'
                      : signupData.confirmPassword && signupData.password === signupData.confirmPassword
                      ? 'border-green-500 focus-visible:ring-green-500'
                      : ''
                  }
                  required
                />
                {signupData.confirmPassword && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2">
                    {signupData.password === signupData.confirmPassword
                      ? <Check className="h-4 w-4 text-green-500" />
                      : <X className="h-4 w-4 text-red-500" />}
                  </span>
                )}
              </div>
              {signupData.confirmPassword && signupData.password !== signupData.confirmPassword && (
                <p className="text-xs text-red-500">Passwords do not match</p>
              )}
            </div>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">Or sign up with</span>
              </div>
            </div>

            <div className="flex justify-center">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => setError("Google Sign-Up failed")}
                size="large"
                width={384}
                disabled={googleLoading}
              />
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating Account...
                </>
              ) : 'Sign Up'}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex justify-center border-t p-4 mt-2">
          <p className="text-sm text-muted-foreground">
            Already have an account? <Link to="/login" className="text-primary hover:underline font-medium">Log in</Link>
          </p>
        </CardFooter>
      </Card>
    </AuthLayout>
  );
}
