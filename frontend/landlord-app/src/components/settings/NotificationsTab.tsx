import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Bell, MessageCircle } from 'lucide-react';
import type { NotificationEventConfig } from '@/types';

const EVENT_GROUPS: { key: string; title: string; description: string }[] = [
  {
    key: 'rent_reminders',
    title: 'Rent reminders',
    description: 'Notify tenants that their rent is due soon.',
  },
  {
    key: 'payment_received',
    title: 'Payment received',
    description: 'Confirm with the tenant when a payment is recorded.',
  },
  {
    key: 'tenant_signup',
    title: 'Tenant signup',
    description: 'Alert when a new tenant signs up in the tenant portal.',
  },
  {
    key: 'login_alerts',
    title: 'Login alerts',
    description: 'Alert when someone signs in to the account.',
  },
];

const CHANNEL_OPTIONS = [
  { key: 'email', label: 'Email' },
  { key: 'sms', label: 'SMS' },
];

const DEFAULT_CHANNELS = ['email', 'sms', 'push'];

interface NotificationsTabProps {
  notifications?: Record<string, unknown>;
  whatsappEnabled: boolean;
  onWhatsappEnabledChange: (enabled: boolean) => void;
  onChange: (patch: Record<string, unknown>) => void;
}

export default function NotificationsTab({
  notifications,
  whatsappEnabled,
  onWhatsappEnabledChange,
  onChange,
}: NotificationsTabProps) {
  const list = notifications || {};
  const channelDefaults = (list.channelDefaults || {}) as Record<string, boolean>;

  const updateEvent = (key: string, patch: Partial<NotificationEventConfig>) => {
    const current = (list[key] || {}) as Partial<NotificationEventConfig>;
    onChange({ [key]: { ...current, ...patch } });
  };

  const toggleEventChannel = (key: string, channelKey: string) => {
    const current = (list[key] || {}) as Partial<NotificationEventConfig>;
    const channels = current.channel ?? [];
    const next = channels.includes(channelKey)
      ? channels.filter((c) => c !== channelKey)
      : [...channels, channelKey];
    updateEvent(key, { channel: next });
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-primary" />
            Notification Preferences
          </CardTitle>
          <CardDescription>
            Configure which events send notifications and how you receive them.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center justify-between gap-4 py-1">
            <div className="space-y-0.5">
              <Label>WhatsApp notifications</Label>
              <p className="text-sm text-muted-foreground">
                Send receipts and reminders via WhatsApp
              </p>
            </div>
            <Switch
              checked={whatsappEnabled}
              onCheckedChange={onWhatsappEnabledChange}
            />
          </div>

          <Separator />

          {EVENT_GROUPS.map((evt, index) => {
            const cfg = (list[evt.key] || {}) as Partial<NotificationEventConfig>;
            const enabled = Boolean(cfg.enabled);

            return (
              <div key={evt.key} className={index > 0 ? 'pt-3' : 'pt-3'}>
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-0.5">
                    <Label>{evt.title}</Label>
                    <p className="text-sm text-muted-foreground">{evt.description}</p>
                    {evt.key === 'rent_reminders' && Array.isArray(cfg.daysBeforeDue) && (
                      <p className="text-xs text-muted-foreground">
                        Reminder sent{' '}
                        {cfg.daysBeforeDue
                          .slice()
                          .sort((a, b) => a - b)
                          .map((d) => `${d} day${d === 1 ? '' : 's'}`)
                          .join(', ')}{' '}
                        before the due date.
                      </p>
                    )}
                  </div>
                  <Switch
                    checked={enabled}
                    onCheckedChange={(v) => updateEvent(evt.key, { enabled: v })}
                  />
                </div>
                <div className="flex flex-wrap items-center gap-2 pt-2">
                  {CHANNEL_OPTIONS.map((ch) => {
                    const active = (cfg.channel ?? []).includes(ch.key);
                    return (
                      <button
                        key={ch.key}
                        type="button"
                        disabled={!enabled}
                        onClick={() => toggleEventChannel(evt.key, ch.key)}
                        className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                          active
                            ? 'border-transparent bg-primary text-primary-foreground'
                            : 'border-border text-muted-foreground hover:border-primary/50'
                        }`}
                      >
                        {ch.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5 text-primary" />
            Default Channels
          </CardTitle>
          <CardDescription>
            Default delivery channels for events that do not specify one.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {DEFAULT_CHANNELS.map((ch) => (
            <div key={ch} className="flex items-center justify-between">
              <Label className="capitalize">{ch}</Label>
              <Switch
                checked={Boolean(channelDefaults[ch])}
                onCheckedChange={(v) =>
                  onChange({
                    channelDefaults: {
                      ...channelDefaults,
                      [ch]: v,
                    },
                  })
                }
              />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}