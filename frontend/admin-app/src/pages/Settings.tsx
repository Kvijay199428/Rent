import { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { api } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import { useTheme } from '@/contexts/ThemeContext';
import type { AppConfig } from '@/types';
import ImportPreviewModal from '../components/modals/ImportPreviewModal';
import ExportPreviewModal from '../components/modals/ExportPreviewModal';
import {
  Receipt,
  UserCircle,
  Palette,
  Save,
  Sun,
  Moon,
  Laptop,
  Upload,
  FileSpreadsheet,
  Database,
  Settings2,
  Bell,
  Shield,
  HardDrive,
  Download,
} from 'lucide-react';

export default function Settings() {
  const whatsappTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [whatsappEditMode, setWhatsappEditMode] = useState(false);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [signatureFile, setSignatureFile] = useState<File | null>(null);
  const [importFiles, setImportFiles] = useState<File[]>([]);
  const [IMPORTPREVIEWDATA, setImportPreviewData] = useState<any>(null);
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const toast = useToast();
  const { theme, effectiveTheme, setTheme } = useTheme();

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await api.getConfig();
      setConfig(data);
    } catch {
      toast.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  useEffect(() => {
    const readonlyByDefault = !!config?.whatsapp?.single_template?.readonly_by_default;
    setWhatsappEditMode(!readonlyByDefault);
  }, [config?.whatsapp?.single_template?.readonly_by_default]);

  async function uploadSignature() {
    if (!signatureFile) return;
    const form = new FormData();
    form.append("file", signatureFile);
    const res = await fetch("/rent/admin/api/settings/upload-signature", {
      method: "POST",
      credentials: "include",
      body: form,
    });
    if (!res.ok) throw new Error("Signature upload failed");
  }

  async function handlePreviewImport(files: File[]) {
    const validFiles = files.filter(f => f.name.endsWith('.xlsx') || f.name.endsWith('.zip'));
    if (!validFiles.length) {
      toast.error("Please select only .xlsx or .zip files.");
      return;
    }
    setImportFiles(validFiles);
    const form = new FormData();
    validFiles.forEach(f => form.append("files", f));

    try {
      const data = await api.importPreview(form);
      setImportPreviewData(data);
    } catch (e: any) {
      toast.error(e.message || "Preview failed");
      setImportFiles([]);
      setImportPreviewData(null);
    }
  }

  const updateWhatsappTemplate = (message: string) => {
    if (!config) return;
    setConfig({
      ...config,
      whatsapp: {
        ...config.whatsapp,
        single_template: {
          label: config.whatsapp?.single_template?.label || 'WhatsApp Template',
          readonly_by_default: config.whatsapp?.single_template?.readonly_by_default ?? true,
          allowed_variables: config.whatsapp?.single_template?.allowed_variables || [],
          default_message: config.whatsapp?.single_template?.default_message || '',
          message,
        },
        country_code: config.whatsapp?.country_code || '91',
      },
    });
  };

  const insertWhatsappVariable = (variable: string) => {
    const el = whatsappTextareaRef.current;
    const currentMessage = config?.whatsapp?.single_template?.message || '';
    if (!el) {
      updateWhatsappTemplate(currentMessage + variable);
      return;
    }
    const start = el.selectionStart ?? currentMessage.length;
    const end = el.selectionEnd ?? currentMessage.length;
    const next = currentMessage.slice(0, start) + variable + currentMessage.slice(end);
    updateWhatsappTemplate(next);
    requestAnimationFrame(() => {
      el.focus();
      const pos = start + variable.length;
      el.setSelectionRange(pos, pos);
    });
  };

  const resetWhatsappTemplate = () => {
    const defaultMessage = config?.whatsapp?.single_template?.default_message || '';
    updateWhatsappTemplate(defaultMessage);
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await api.saveConfig({
        landlord: config.landlord,
        billing: config.billing,
        whatsapp: config.whatsapp,
      });
      await uploadSignature();
      toast.success('Settings saved successfully');
      setSignatureFile(null);
    } catch {
      toast.error('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const updateLandlord = (field: string, value: unknown) => {
    if (!config) return;
    setConfig({ ...config, landlord: { ...config.landlord, [field]: value } });
  };

  const updateBilling = (field: string, value: number) => {
    if (!config) return;
    setConfig({ ...config, billing: { ...config.billing, [field]: value } });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!config) return null;

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage application settings, data import/export, and configurations.
        </p>
      </div>

      <Tabs defaultValue="data" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4 lg:w-[400px]">
          <TabsTrigger value="data" className="gap-1">
            <Database className="h-4 w-4" />
            Data
          </TabsTrigger>
          <TabsTrigger value="general" className="gap-1">
            <Settings2 className="h-4 w-4" />
            General
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-1">
            <Bell className="h-4 w-4" />
            Alerts
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-1">
            <Shield className="h-4 w-4" />
            Security
          </TabsTrigger>
        </TabsList>

        {/* ─── DATA TAB: Import / Export ─── */}
        <TabsContent value="data" className="space-y-4">
          {/* Import Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5 text-primary" />
                Import Data
              </CardTitle>
              <CardDescription>
                Import tenant profiles and rent receipts from Excel spreadsheets or ZIP archives.
                Download the template below to ensure correct formatting.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-3">
                <div
                  className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-primary transition-colors flex flex-col items-center justify-center gap-2 flex-1"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files?.length) {
                      handlePreviewImport(Array.from(e.dataTransfer.files));
                    }
                  }}
                  onClick={() => document.getElementById('import-file')?.click()}
                >
                  <Upload className="h-8 w-8 mx-auto mb-2 text-primary" />
                  <h6 className="font-bold">
                    <label htmlFor="import-file" className="cursor-pointer" onClick={(e) => e.stopPropagation()}>
                      {importFiles.length > 0 ? `${importFiles.length} file(s) selected` : "Drag & Drop .xlsx / .zip Files or Click"}
                    </label>
                  </h6>
                  <p className="text-xs text-muted-foreground mt-1">Select one or more .xlsx files or a .zip.</p>
                  <input
                    id="import-file"
                    type="file"
                    accept=".xlsx,.zip"
                    multiple
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.length) {
                        handlePreviewImport(Array.from(e.target.files));
                      }
                      e.target.value = '';
                    }}
                  />
                </div>

                <Button
                  variant="outline"
                  onClick={() => window.open(api.downloadTemplate(), '_blank')}
                  className="gap-2 h-auto py-6"
                >
                  <Download className="h-4 w-4" />
                  <div className="text-left">
                    <div className="text-xs font-bold">Blank Template</div>
                  </div>
                </Button>
              </div>

              <ImportPreviewModal
                open={!!IMPORTPREVIEWDATA}
                onOpenChange={(open: boolean) => {
                  if (!open) {
                    setImportPreviewData(null);
                    setImportFiles([]);
                  }
                }}
                previewData={IMPORTPREVIEWDATA}
                files={importFiles}
                onImportSuccess={() => {
                  setImportPreviewData(null);
                  setImportFiles([]);
                  loadConfig();
                }}
              />

              <div className="rounded-lg border bg-muted/30 p-4">
                <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                  <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
                  Supported Formats
                </h4>
                <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                  <li>
                    <strong>.xlsx</strong> — Single Excel file with{" "}
                    <code>Tenant_Profile</code> and <code>Rent_Receipts</code> sheets
                  </li>
                  <li>
                    <strong>.zip</strong> — Archive containing multiple .xlsx files
                  </li>
                  <li>
                    Required columns: tenantId, tenantName, Phone, Rent, Water, electricityRate
                  </li>
                </ul>
              </div>
            </CardContent>
          </Card>

          {/* Export Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Download className="h-5 w-5 text-primary" />
                Export Data
              </CardTitle>
              <CardDescription>
                Download all tenant and receipt data in your preferred format.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3">
                <Button onClick={() => setExportModalOpen(true)}>
                  <Download className="mr-2 h-4 w-4" />
                  Preview & Export Data
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── GENERAL TAB: Billing + Landlord + Appearance ─── */}
        <TabsContent value="general" className="space-y-4">
          {/* Billing Defaults */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Receipt className="h-5 w-5 text-primary" />
                Billing Defaults
              </CardTitle>
              <CardDescription>
                These values will be automatically assigned to <strong>newly created tenants</strong>. Existing tenants will not be affected.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Default Rent (₹)</Label>
                  <Input type="number" value={config.billing.rent} onChange={(e) => updateBilling('rent', parseFloat(e.target.value) || 0)} />
                </div>
                <div className="space-y-2">
                  <Label>Default Water (₹)</Label>
                  <Input type="number" value={config.billing.water} onChange={(e) => updateBilling('water', parseFloat(e.target.value) || 0)} />
                </div>
                <div className="space-y-2">
                  <Label>Electricity Rate (₹/unit)</Label>
                  <Input type="number" step="0.1" value={config.billing.electricityRate} onChange={(e) => updateBilling('electricityRate', parseFloat(e.target.value) || 0)} />
                </div>
                <div className="space-y-2">
                  <Label>Default Meter Reading</Label>
                  <Input type="number" step="0.1" value={config.billing.previousMeter_reading} onChange={(e) => updateBilling('previousMeter_reading', parseFloat(e.target.value) || 0)} />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Additional Person Charge (₹)</Label>
                <Input type="number" value={config.billing.additionalPersonCharge} onChange={(e) => updateBilling('additionalPersonCharge', parseFloat(e.target.value) || 0)} />
              </div>
            </CardContent>
          </Card>

          {/* Landlord Info */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserCircle className="h-5 w-5 text-primary" />
                Landlord Information
              </CardTitle>
              <CardDescription>
                This information will be printed on the generated PDF receipts.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Landlord Name</Label>
                <Input value={config.landlord.name} onChange={(e) => updateLandlord('name', e.target.value)} required />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Phone Number</Label>
                  <Input value={config.landlord.phone} onChange={(e) => updateLandlord('phone', e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Email Address</Label>
                  <Input type="email" value={config.landlord.email} onChange={(e) => updateLandlord('email', e.target.value)} />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Property Address</Label>
                <Textarea value={config.landlord.address} onChange={(e) => updateLandlord('address', e.target.value)} rows={3} />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>PAN Number</Label>
                  <Input value={config.landlord.pan} onChange={(e) => updateLandlord('pan', e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Signature Text</Label>
                  <Input value={config.landlord.signature_text} onChange={(e) => updateLandlord('signature_text', e.target.value)} />
                </div>
              </div>

              <Separator />

              <h5 className="font-bold text-sm">
                Bank Details <span className="ml-2 text-xs font-normal bg-secondary px-2 py-0.5 rounded">Optional</span>
              </h5>
              <p className="text-xs text-muted-foreground">If provided, payment instructions will be added to your receipts.</p>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Account Holder Name</Label>
                  <Input value={config.landlord.bank_account_name} onChange={(e) => updateLandlord('bank_account_name', e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Account Number</Label>
                  <Input value={config.landlord.bank_account_number} onChange={(e) => updateLandlord('bank_account_number', e.target.value)} />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Bank Name</Label>
                  <Input value={config.landlord.bank_name} onChange={(e) => updateLandlord('bank_name', e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Branch</Label>
                  <Input value={config.landlord.bank_branch} onChange={(e) => updateLandlord('bank_branch', e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>IFSC Code</Label>
                  <Input value={config.landlord.bank_ifsc} onChange={(e) => updateLandlord('bank_ifsc', e.target.value.toUpperCase())} className="uppercase" />
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Switch
                  checked={config.landlord.mask_bank_account}
                  onCheckedChange={(v) => updateLandlord('mask_bank_account', v)}
                />
                <Label className="cursor-pointer">Mask account number on printed receipts</Label>
              </div>

              <Separator />

              <h5 className="font-bold text-sm">Digital Signature</h5>
              <div
                className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-primary transition-colors flex flex-col items-center justify-center gap-2"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  setSignatureFile(e.dataTransfer.files?.[0] ?? null);
                }}
                onClick={() => document.getElementById('signature-upload')?.click()}
              >
                {(signatureFile || config.landlord.signature_image) ? (
                  <img
                    src={signatureFile ? URL.createObjectURL(signatureFile) : `/rent/static/uploads/landlord_signature_flattened.png?t=${new Date().getTime()}`}
                    alt="Signature Preview"
                    className="max-h-24 object-contain mb-2 border rounded p-1 bg-white"
                  />
                ) : (
                  <Upload className="h-8 w-8 mx-auto mb-2 text-primary" />
                )}
                <h6 className="font-bold">
                  <label htmlFor="signature-upload" className="cursor-pointer" onClick={(e) => e.stopPropagation()}>
                    {signatureFile ? signatureFile.name : "Drag & Drop Signature or Click"}
                  </label>
                </h6>
                <p className="text-xs text-muted-foreground mt-1">Accepted: PNG, JPG, WEBP. Max size: 2MB.</p>
                <input
                  id="signature-upload"
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => setSignatureFile(e.target.files?.[0] ?? null)}
                />
              </div>

              <Separator />

              <h5 className="font-bold text-sm">
                {config.whatsapp?.single_template?.label || 'WhatsApp Template'}
              </h5>

              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs text-muted-foreground">
                    Build the tenant WhatsApp message using the allowed variables below.
                  </p>
                  <div className="flex gap-2">
                    {!whatsappEditMode ? (
                      <Button type="button" variant="outline" size="sm" onClick={() => setWhatsappEditMode(true)}>
                        Edit
                      </Button>
                    ) : (
                      <>
                        <Button type="button" variant="outline" size="sm" onClick={resetWhatsappTemplate}>
                          Reset
                        </Button>
                        <Button type="button" variant="secondary" size="sm" onClick={() => setWhatsappEditMode(false)}>
                          Lock
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {(config.whatsapp?.single_template?.allowed_variables || []).map((variable) => (
                    <Button
                      key={variable}
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={!whatsappEditMode}
                      onClick={() => insertWhatsappVariable(variable)}
                      className="rounded-full"
                    >
                      {variable}
                    </Button>
                  ))}
                </div>

                <Textarea
                  ref={whatsappTextareaRef}
                  value={config.whatsapp?.single_template?.message || ''}
                  readOnly={!whatsappEditMode}
                  disabled={!whatsappEditMode}
                  onChange={(e) => updateWhatsappTemplate(e.target.value)}
                  rows={8}
                  className={!whatsappEditMode ? 'opacity-80 cursor-not-allowed' : ''}
                />

                <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground">
                  <span>Mode: {whatsappEditMode ? 'Editable' : 'Read only'}</span>
                  <span>Country code: {config.whatsapp?.country_code || '91'}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Appearance */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="h-5 w-5 text-primary" />
                Appearance
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
                  <div className="font-medium capitalize">{effectiveTheme}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── NOTIFICATIONS TAB ─── */}
        <TabsContent value="notifications" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5 text-primary" />
                Notification Preferences
              </CardTitle>
              <CardDescription>
                Configure how and when you receive alerts.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>WhatsApp Notifications</Label>
                  <p className="text-sm text-muted-foreground">
                    Send receipts and reminders via WhatsApp
                  </p>
                </div>
                <Switch
                  checked={config.whatsapp?.enabled ?? true}
                  onCheckedChange={(v) => {
                    if (!config) return;
                    setConfig({
                      ...config,
                      whatsapp: { ...config.whatsapp, enabled: v }
                    });
                  }}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── SECURITY TAB ─── */}
        <TabsContent value="security" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                Security Settings
              </CardTitle>
              <CardDescription>
                Configure security and privacy options for receipts.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Mask Bank Account</Label>
                  <p className="text-sm text-muted-foreground">
                    Hide full account number on printed receipts
                  </p>
                </div>
                <Switch
                  checked={config.landlord.mask_bank_account}
                  onCheckedChange={(v) => updateLandlord('mask_bank_account', v)}
                />
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Show Signature</Label>
                  <p className="text-sm text-muted-foreground">
                    Display landlord signature on receipts
                  </p>
                </div>
                <Switch
                  checked={!!config.landlord.signature_image || !!signatureFile}
                  onCheckedChange={(v) => {
                    // Toggle signature display is handled by presence of image
                    if (!v && config.landlord.signature_image) {
                      updateLandlord('signature_image', '');
                    }
                  }}
                  disabled={!config.landlord.signature_image && !signatureFile}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button size="lg" onClick={handleSave} disabled={saving} className="rounded-full px-8">
          <Save className="h-4 w-4 mr-2" />
          {saving ? 'Saving...' : 'Save All Settings'}
        </Button>
      </div>

      <ExportPreviewModal
        open={exportModalOpen}
        onOpenChange={setExportModalOpen}
      />
    </div>
  );
}