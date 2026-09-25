import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { User, KeyRound, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { api } from '@/services/api';
import PhoneInputField from '@shared/phone/PhoneInput';
import { ChangePasswordDialog } from './ChangePasswordDialog';

export default function ProfileTab() {
  const { landlordUuid, username, refreshMe } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);

  useEffect(() => {
    if (!landlordUuid) return;
    let cancelled = false;
    (async () => {
      try {
        const result = await api.getProfile(landlordUuid);
        if (cancelled) return;
        if (result.profile) {
          setFullName(result.profile.fullName || '');
          setEmail(result.profile.email || '');
          setPhone(result.profile.phone || '');
        }
      } catch {
        if (!cancelled) setError('Failed to load profile.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [landlordUuid]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!landlordUuid) return;
    setError('');
    setSuccess('');
    setSaving(true);
    try {
      await api.updateProfile(landlordUuid, {
        fullName,
        email,
        phone: phone || null,
      });
      await refreshMe();
      setSuccess('Profile updated successfully!');
      setTimeout(() => setSuccess(''), 5000);
    } catch (err: any) {
      setError(err?.message || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5 text-primary" />
            Profile
          </CardTitle>
          <CardDescription>
            Manage your personal details. Username cannot be changed.
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

          <form onSubmit={handleSave} className="space-y-4">
            <div className="space-y-2">
              <Label>Username</Label>
              <Input value={username || ''} readOnly disabled />
              <p className="text-xs text-muted-foreground">Your username is used for login and cannot be changed.</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="profile-fullName">Full Name</Label>
              <Input
                id="profile-fullName"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your full name"
                minLength={2}
                maxLength={120}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="profile-email">Email</Label>
              <Input
                id="profile-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                maxLength={254}
              />
            </div>

            <div className="space-y-2">
              <Label>Phone</Label>
              <PhoneInputField value={phone} onChange={(value) => setPhone(value || '')} />
            </div>

            <div className="space-y-2 pt-2">
              <Label>Password</Label>
              <div className="flex items-center justify-between rounded-lg border p-4">
                <div>
                  <p className="text-sm font-medium">Change Password</p>
                  <p className="text-sm text-muted-foreground">Update your login password.</p>
                </div>
                <Button type="button" variant="outline" onClick={() => setShowPasswordDialog(true)}>
                  <KeyRound className="h-4 w-4 mr-2" />
                  Change Password
                </Button>
              </div>
            </div>

            <div className="flex justify-end">
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : 'Save Profile'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <ChangePasswordDialog open={showPasswordDialog} onOpenChange={setShowPasswordDialog} />
    </>
  );
}