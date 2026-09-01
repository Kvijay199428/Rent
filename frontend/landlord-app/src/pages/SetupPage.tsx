import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { AlertTriangle, Building2, Plus, Trash2, UserRound, CheckCircle2, Upload, PenLine, ChevronLeft, ChevronRight, Landmark } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/services/api";
import { useAuth } from "@/contexts/AuthContext";
import LoadingOverlay from "@shared/loading/LoadingOverlay";
import PhoneInputField from "@shared/phone/PhoneInput";
import { Logo } from "@shared/brand/Logo";

interface PropertyRow {
  property_name: string;
  address: string;
}

interface LandlordProfile {
  name: string;
  phone: string;
  email: string;
  address: string;
  signature_image: string;
  bank_account_name: string;
  bank_account_number: string;
  bank_name: string;
  bank_branch: string;
  bank_ifsc: string;
  mask_bank_account: boolean;
}

const STEPS = [
  { key: "details", label: "Your details" },
  { key: "properties", label: "Properties" },
  { key: "bank", label: "Bank" },
  { key: "signature", label: "Signature" },
];

export default function SetupPage() {
  const navigate = useNavigate();
  const { landlordUuid, setupCompleted, refreshMe, setSetupState } = useAuth();

  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<LandlordProfile>({
    name: "",
    phone: "",
    email: "",
    address: "",
    signature_image: "",
    bank_account_name: "",
    bank_account_number: "",
    bank_name: "",
    bank_branch: "",
    bank_ifsc: "",
    mask_bank_account: false,
  });
  const [properties, setProperties] = useState<PropertyRow[]>([
    { property_name: "Property 1", address: "" },
  ]);
  const [signatureFile, setSignatureFile] = useState<File | null>(null);
  const [signaturePreview, setSignaturePreview] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const destinations = useMemo(() => {
    const uuid = landlordUuid || "";
    return {
      home: uuid ? `/${uuid}/dashboard` : "/dashboard",
      settings: uuid ? `/${uuid}/settings` : "/settings",
    };
  }, [landlordUuid]);

  if (setupCompleted) {
    return null;
  }

  const defaultName = (index: number) => `Property ${index + 1}`;

  const updateProperty = (index: number, patch: Partial<PropertyRow>) => {
    setProperties((prev) =>
      prev.map((p, i) => (i === index ? { ...p, ...patch } : p))
    );
  };

  const addProperty = () => {
    setProperties((prev) => {
      const nextName = `Property ${prev.length + 1}`;
      return [...prev, { property_name: nextName, address: "" }];
    });
  };

  const removeProperty = (index: number) => {
    setProperties((prev) => {
      const next = prev.filter((_, i) => i !== index);
      return next.length ? next : [{ property_name: "Property 1", address: "" }];
    });
  };

  const handleSignatureFile = (file: File | null) => {
    if (!file) {
      setSignatureFile(null);
      setSignaturePreview("");
      return;
    }
    if (!file.type.startsWith("image/")) {
      setError("Please select an image file for your signature.");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setError("Signature image must be under 2MB.");
      return;
    }
    setError("");
    setSignatureFile(file);
    setSignaturePreview(URL.createObjectURL(file));
  };

  const nextStep = () => {
    setError("");
    if (step === 1) {
      const validProps = properties
        .map((p) => p.property_name.trim())
        .filter(Boolean);
      if (!validProps.length) {
        setError("Add at least one property to continue.");
        return;
      }
    }
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  };

  const handleComplete = async () => {
    setError("");
    const validProps = properties
      .map((p) => ({
        property_name: p.property_name.trim() || defaultName(0),
        address: p.address.trim(),
      }))
      .filter((p) => p.property_name);

    if (!validProps.length) {
      setError("Add at least one property to continue.");
      setStep(1);
      return;
    }

    setSaving(true);
    try {
      let signaturePath = "";
      if (signatureFile && landlordUuid) {
        signaturePath = await api.uploadSignature(landlordUuid, signatureFile);
      }
      await api.completeSetup({
        landlord: { ...profile, signature_image: signaturePath },
        properties: validProps,
      });
      setSetupState(true, false);
      toast.success("Setup complete", { description: "Welcome to PROPAURA. You can manage properties any time from Settings." });
      await refreshMe();
      navigate(destinations.home, { replace: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to complete setup. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const handleCompleteLater = async () => {
    setError("");
    setSaving(true);
    try {
      await api.skipSetup();
      setSetupState(false, true);
      toast.success("You can complete setup later from Settings.");
      await refreshMe();
      navigate(destinations.home, { replace: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to skip setup. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 py-8 px-4">
        <div className="max-w-2xl mx-auto space-y-6">
          <Card className="shadow-xl">
            <CardHeader className="space-y-1">
              <div className="flex items-center justify-center mb-4">
                <div className="p-3 bg-primary/10 rounded-full">
                  <Building2 className="h-8 w-8 text-primary" />
                </div>
              </div>
              <CardTitle className="text-2xl text-center">Welcome to <Logo height={22} /></CardTitle>
              <CardDescription className="text-center">
                Let us set up your account. Add your details and properties so billing is ready to use.
              </CardDescription>

              {/* Step indicator */}
              <div className="flex items-center justify-center gap-2 pt-4">
                {STEPS.map((s, i) => (
                  <div key={s.key} className="flex items-center gap-2">
                    {i > 0 && <div className={`h-px w-6 ${i <= step ? "bg-primary" : "bg-muted"}`} />}
                    <div
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                        i === step
                          ? "bg-primary text-primary-foreground"
                          : i < step
                            ? "bg-primary/15 text-primary"
                            : "bg-muted text-muted-foreground"
                      }`}
                    >
                      {i < step ? (
                        <CheckCircle2 className="h-3.5 w-3.5" />
                      ) : (
                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                      )}
                      {s.label}
                    </div>
                  </div>
                ))}
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              {error && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {step === 0 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <UserRound className="h-5 w-5 text-primary" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                      Your details
                    </h3>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="setup-name">Landlord name</Label>
                      <Input
                        id="setup-name"
                        value={profile.name}
                        onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                        placeholder="e.g. Ramesh Kumar"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="setup-phone">Phone</Label>
                      <PhoneInputField
                        id="setup-phone"
                        value={profile.phone}
                        onChange={(value) => setProfile({ ...profile, phone: value || "" })}
                        placeholder="Mobile number"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="setup-email">Email</Label>
                      <Input
                        id="setup-email"
                        type="email"
                        value={profile.email}
                        onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                        placeholder="you@example.com"
                      />
                    </div>
                    <div className="space-y-2 sm:col-span-2">
                      <Label htmlFor="setup-address">Address</Label>
                      <Input
                        id="setup-address"
                        value={profile.address}
                        onChange={(e) => setProfile({ ...profile, address: e.target.value })}
                        placeholder="This address prints on your rent receipts"
                      />
                    </div>
                  </div>
                </div>
              )}

              {step === 1 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Building2 className="h-5 w-5 text-primary" />
                      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                        Properties
                      </h3>
                    </div>
                    <Button type="button" variant="outline" size="sm" onClick={addProperty}>
                      <Plus className="h-4 w-4 mr-1" /> Add property
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground -mt-2">
                    You can have one or more properties, each with its own tenants. Add more later from Settings.
                  </p>

                  <div className="space-y-4">
                    {properties.map((p, index) => (
                      <div key={index} className="rounded-md border p-4 space-y-3">
                        <div className="flex items-center justify-between gap-2">
                          <Label className="text-xs font-medium text-muted-foreground">
                            {p.property_name || defaultName(index)}
                          </Label>
                          {properties.length > 1 && (
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-muted-foreground hover:text-destructive"
                              onClick={() => removeProperty(index)}
                              aria-label={`Remove ${p.property_name || defaultName(index)}`}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div className="space-y-1.5">
                            <Label htmlFor={`prop-name-${index}`} className="text-xs">Property name</Label>
                            <Input
                              id={`prop-name-${index}`}
                              value={p.property_name}
                              onChange={(e) => updateProperty(index, { property_name: e.target.value })}
                              placeholder={defaultName(index)}
                            />
                          </div>
                          <div className="space-y-1.5">
                            <Label htmlFor={`prop-address-${index}`} className="text-xs">Address</Label>
                            <Input
                              id={`prop-address-${index}`}
                              value={p.address}
                              onChange={(e) => updateProperty(index, { address: e.target.value })}
                              placeholder="Property address (optional)"
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Landmark className="h-5 w-5 text-primary" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                      Bank details
                    </h3>
                  </div>
                  <p className="text-xs text-muted-foreground -mt-2">
                    Optional — if provided, payment instructions are added to your rent receipts. You can edit this later from Settings.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="setup-bank-name">Account Holder Name</Label>
                      <Input
                        id="setup-bank-name"
                        value={profile.bank_account_name}
                        onChange={(e) => setProfile({ ...profile, bank_account_name: e.target.value })}
                        placeholder="e.g. Ramesh Kumar"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="setup-bank-number">Account Number</Label>
                      <Input
                        id="setup-bank-number"
                        value={profile.bank_account_number}
                        onChange={(e) => setProfile({ ...profile, bank_account_number: e.target.value })}
                        placeholder="Account number"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="setup-bank-name-2">Bank Name</Label>
                      <Input
                        id="setup-bank-name-2"
                        value={profile.bank_name}
                        onChange={(e) => setProfile({ ...profile, bank_name: e.target.value })}
                        placeholder="e.g. HDFC Bank"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="setup-bank-branch">Branch</Label>
                      <Input
                        id="setup-bank-branch"
                        value={profile.bank_branch}
                        onChange={(e) => setProfile({ ...profile, bank_branch: e.target.value })}
                        placeholder="e.g. Koramangala"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="setup-bank-ifsc">IFSC Code</Label>
                      <Input
                        id="setup-bank-ifsc"
                        value={profile.bank_ifsc}
                        onChange={(e) => setProfile({ ...profile, bank_ifsc: e.target.value.toUpperCase() })}
                        placeholder="e.g. HDFC0001234"
                        className="uppercase"
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Switch
                      id="setup-bank-mask"
                      checked={profile.mask_bank_account}
                      onCheckedChange={(v) => setProfile({ ...profile, mask_bank_account: v })}
                    />
                    <Label htmlFor="setup-bank-mask" className="cursor-pointer">Mask account number on printed receipts</Label>
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <PenLine className="h-5 w-5 text-primary" />
                    <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                      Digital Signature
                    </h3>
                  </div>
                  <p className="text-xs text-muted-foreground -mt-2">
                    Optional — your signature prints on rent receipts. You can add it later from Settings.
                  </p>

                  <div
                    className="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer hover:border-primary transition-colors flex flex-col items-center justify-center gap-2"
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      handleSignatureFile(e.dataTransfer.files?.[0] ?? null);
                    }}
                    onClick={() => document.getElementById("signature-upload")?.click()}
                  >
                    {signaturePreview ? (
                      <img
                        src={signaturePreview}
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
                      onChange={(e) => handleSignatureFile(e.target.files?.[0] ?? null)}
                    />
                  </div>
                  {signatureFile && (
                    <div className="flex justify-end">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSignatureFile(null)}
                      >
                        Remove signature
                      </Button>
                    </div>
                  )}

                  <Separator />

                  <div className="rounded-md border bg-muted/30 p-4 space-y-1.5">
                    <p className="text-sm font-semibold">Review</p>
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">{profile.name || "Landlord"}</span>
                      {profile.phone && ` · ${profile.phone}`}
                      {profile.email && ` · ${profile.email}`}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {properties.map((p, i) => p.property_name.trim() || defaultName(i)).join(", ")}
                    </p>
                    {profile.bank_name && (
                      <p className="text-xs text-muted-foreground">
                        {profile.bank_account_name || profile.bank_name}
                        {profile.bank_name && ` · ${profile.bank_name}`}
                        {profile.bank_branch && ` · ${profile.bank_branch}`}
                        {profile.bank_ifsc && ` · ${profile.bank_ifsc}`}
                      </p>
                    )}
                  </div>
                </div>
              )}

              <div className="flex flex-col gap-3 pt-2">
                <div className="flex gap-3">
                  {step > 0 && (
                    <Button variant="outline" className="flex-1" onClick={() => setStep((s) => Math.max(s - 1, 0))} disabled={saving}>
                      <ChevronLeft className="h-4 w-4 mr-1" /> Back
                    </Button>
                  )}
                  {step < STEPS.length - 1 ? (
                    <Button className="flex-1" onClick={nextStep} disabled={saving}>
                      Continue <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  ) : (
                    <Button className="flex-1" onClick={handleComplete} disabled={saving}>
                      <CheckCircle2 className="h-4 w-4 mr-2" />
                      {saving ? "Saving…" : "Save & Continue"}
                    </Button>
                  )}
                </div>
                <Button variant="ghost" className="w-full" onClick={handleCompleteLater} disabled={saving}>
                  Complete Later
                </Button>
                <p className="text-xs text-muted-foreground text-center">
                  You can set up your properties later from{" "}
                  <button
                    className="underline underline-offset-2 text-primary"
                    onClick={() => navigate(destinations.settings)}
                  >
                    Settings
                  </button>
                  .
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
      {saving && <LoadingOverlay label="Saving your setup…" />}
    </>
  );
}
