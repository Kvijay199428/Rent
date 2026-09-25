import { useTheme } from '@/contexts/ThemeContext';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Accessibility,
  Globe,
  Laptop,
  Moon,
  Palette,
  Sun,
} from 'lucide-react';
import type { UiPreferences } from '@/types';

const LANGUAGE_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'ta', label: 'தமிழ்' },
  { value: 'hi', label: 'हिन्दी' },
];

const LOCALE_OPTIONS = [
  { value: 'en-US', label: 'English (US)' },
  { value: 'en-IN', label: 'English (India)' },
  { value: 'en-GB', label: 'English (UK)' },
  { value: 'ta-IN', label: 'தமிழ் (India)' },
  { value: 'hi-IN', label: 'हिन्दी (India)' },
];

const CURRENCY_OPTIONS = [
  { value: 'INR', label: 'INR · ₹' },
  { value: 'USD', label: 'USD · $' },
  { value: 'EUR', label: 'EUR · €' },
  { value: 'GBP', label: 'GBP · £' },
  { value: 'AED', label: 'AED · د.إ' },
];

const DATE_FORMAT_OPTIONS = [
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD' },
  { value: 'DD-MM-YYYY', label: 'DD-MM-YYYY' },
  { value: 'MM-DD-YYYY', label: 'MM-DD-YYYY' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY' },
];

const TIME_FORMAT_OPTIONS = [
  { value: '24h', label: '24-hour (18:30)' },
  { value: '12h', label: '12-hour (06:30 PM)' },
];

const WEEK_STARTS_OPTIONS = [
  { value: 'monday', label: 'Monday' },
  { value: 'sunday', label: 'Sunday' },
];

export const DEFAULT_UI_PREFERENCES: UiPreferences = {
  language: 'en',
  locale: 'en-US',
  currency: 'INR',
  dateFormat: 'YYYY-MM-DD',
  timeFormat: '24h',
  weekStartsOn: 'monday',
  reduceMotion: false,
  highContrast: false,
  compactMode: false,
};

interface AppearanceTabProps {
  preferences?: Partial<UiPreferences>;
  onChange: (patch: Partial<UiPreferences>) => void;
}

interface SelectFieldProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onValueChange: (value: string) => void;
}

function SelectField({ label, value, options, onValueChange }: SelectFieldProps) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger className="w-full">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

export default function AppearanceTab({ preferences, onChange }: AppearanceTabProps) {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const prefs: UiPreferences = { ...DEFAULT_UI_PREFERENCES, ...preferences };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="h-5 w-5 text-primary" />
            Theme
          </CardTitle>
          <CardDescription>
            Choose how the app should look across all pages.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            {[
              { value: 'light' as const, label: 'Light', desc: 'Bright interface for daytime use.', icon: Sun },
              { value: 'dark' as const, label: 'Dark', desc: 'Low-glare interface for night use.', icon: Moon },
              { value: 'system' as const, label: 'System', desc: 'Automatically follows your device preference.', icon: Laptop },
            ].map((option) => (
              <button
                key={option.value}
                onClick={() => setTheme(option.value)}
                className={`p-4 rounded-xl border-2 text-left transition-all ${theme === option.value
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-primary/50'
                  }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${option.value === 'light' ? 'bg-amber-100 text-amber-600' :
                    option.value === 'dark' ? 'bg-indigo-100 text-indigo-600' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                    <option.icon className="h-4 w-4" />
                  </div>
                  {theme === option.value && (
                    <span className="text-xs bg-primary text-primary-foreground px-2 py-0.5 rounded-full">Active</span>
                  )}
                </div>
                <div className="font-bold text-sm">{option.label}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{option.desc}</div>
              </button>
            ))}
          </div>
          <div className="flex gap-6 mt-4 text-sm">
            <div>
              <span className="text-xs text-muted-foreground uppercase font-semibold">Selected</span>
              <div className="font-medium capitalize">{theme}</div>
            </div>
            <div>
              <span className="text-xs text-muted-foreground uppercase font-semibold">Applied now</span>
              <div className="font-medium capitalize">{resolvedTheme}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5 text-primary" />
            Regional & Formatting
          </CardTitle>
          <CardDescription>
            Control how dates, times and amounts are displayed in bills and reports.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField
              label="Language"
              value={prefs.language}
              options={LANGUAGE_OPTIONS}
              onValueChange={(v) => onChange({ language: v })}
            />
            <SelectField
              label="Locale"
              value={prefs.locale}
              options={LOCALE_OPTIONS}
              onValueChange={(v) => onChange({ locale: v })}
            />
            <SelectField
              label="Currency"
              value={prefs.currency}
              options={CURRENCY_OPTIONS}
              onValueChange={(v) => onChange({ currency: v })}
            />
            <SelectField
              label="Date format"
              value={prefs.dateFormat}
              options={DATE_FORMAT_OPTIONS}
              onValueChange={(v) => onChange({ dateFormat: v })}
            />
            <SelectField
              label="Time format"
              value={prefs.timeFormat}
              options={TIME_FORMAT_OPTIONS}
              onValueChange={(v) => onChange({ timeFormat: v })}
            />
            <SelectField
              label="Week starts on"
              value={prefs.weekStartsOn}
              options={WEEK_STARTS_OPTIONS}
              onValueChange={(v) => onChange({ weekStartsOn: v })}
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Accessibility className="h-5 w-5 text-primary" />
            Accessibility
          </CardTitle>
          <CardDescription>
            Adapt the interface to your comfort and needs.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5">
              <Label>Reduce motion</Label>
              <p className="text-sm text-muted-foreground">Minimize animations and screen transitions.</p>
            </div>
            <Switch checked={prefs.reduceMotion} onCheckedChange={(v) => onChange({ reduceMotion: v })} />
          </div>
          <Separator />
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5">
              <Label>High contrast</Label>
              <p className="text-sm text-muted-foreground">Increase contrast to make text more readable.</p>
            </div>
            <Switch checked={prefs.highContrast} onCheckedChange={(v) => onChange({ highContrast: v })} />
          </div>
          <Separator />
          <div className="flex items-center justify-between gap-4">
            <div className="space-y-0.5">
              <Label>Compact mode</Label>
              <p className="text-sm text-muted-foreground">Reduce spacing and density across the app.</p>
            </div>
            <Switch checked={prefs.compactMode} onCheckedChange={(v) => onChange({ compactMode: v })} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}