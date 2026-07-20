import { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Users,
  Upload,
  FileText,
  Trash2,
  UserX,
  X,
  Loader2,
  CalendarDays,
  Phone,
  MapPin,
  Clock,
} from "lucide-react";
import { api } from "@/services/api";
import type { Occupant, Tenant } from "@/types";
import { toast } from "sonner";

// ─── helpers ─────────────────────────────────────────────────────────────────

function isPdf(filename: string) {
  return filename.toLowerCase().endsWith(".pdf");
}

function getUuid(o: Occupant): string {
  return o.occupantUuid || o["Occupant UUID"] || "";
}

function daysStayed(residentSince?: string): string {
  if (!residentSince) return "";
  try {
    const days = Math.floor((Date.now() - new Date(residentSince).getTime()) / 86_400_000);
    if (isNaN(days) || days < 0) return "";
    return `${days} day${days === 1 ? "" : "s"}`;
  } catch {
    return "";
  }
}

function formatDate(iso?: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return iso;
  }
}

// Maps display labels to the possible field names returned by get_occupants
const DOC_LABEL_KEYS: Record<string, (keyof Occupant)[]> = {
  "Aadhaar Combined": ["aadhaarcombined", "aadhaar_combined", "Aadhaar Combined"],
  "Aadhaar Front": ["aadhaarfront", "aadhaar_front", "Aadhaar Front"],
  "Aadhaar Back": ["aadhaarback", "aadhaar_back", "Aadhaar Back"],
  "Emp Front": ["empfront", "emp_front", "Emp Front"],
  "Emp Back": ["empback", "emp_back", "Emp Back"],
};
const DOC_LABELS = Object.keys(DOC_LABEL_KEYS) as (keyof typeof DOC_LABEL_KEYS)[];

function getDocFilename(o: Occupant, label: string): string {
  for (const k of DOC_LABEL_KEYS[label] ?? []) {
    const v = o[k] as string | undefined;
    if (v) return v;
  }
  return "";
}

// ─── Upload form ──────────────────────────────────────────────────────────────

function UploadForm({
  tenantId,
  onSuccess,
  onCancel,
}: {
  tenantId: number;
  onSuccess: (newUuid: string) => void;
  onCancel: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [aadhaarMode, setAadhaarMode] = useState<"combined" | "split">("combined");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const rawForm = new FormData(e.currentTarget);
    const combined = rawForm.get("aadhaarcombined") as File | null;
    const front = rawForm.get("aadhaarfront") as File | null;
    const back = rawForm.get("aadhaarback") as File | null;

    const hasCombined = combined instanceof File && combined.size > 0;
    const hasBoth =
      front instanceof File && front.size > 0 &&
      back instanceof File && back.size > 0;

    if (!hasCombined && !hasBoth) {
      toast.error("Upload Aadhaar combined, or both front and back.");
      return;
    }

    // Build clean FormData — exclude empty file inputs from the inactive Aadhaar mode
    const data = new FormData();
    data.append("name", (rawForm.get("name") as string)?.trim() ?? "");
    data.append("mobile", (rawForm.get("mobile") as string)?.trim() ?? "");
    data.append("address", (rawForm.get("address") as string)?.trim() ?? "");
    data.append("residentSince", rawForm.get("residentSince") as string ?? "");

    if (hasCombined) data.append("aadhaarcombined", combined!);
    if (hasBoth) {
      data.append("aadhaarfront", front!);
      data.append("aadhaarback", back!);
    }
    const empFront = rawForm.get("empfront") as File | null;
    const empBack = rawForm.get("empback") as File | null;
    if (empFront instanceof File && empFront.size > 0) data.append("empfront", empFront);
    if (empBack instanceof File && empBack.size > 0) data.append("empback", empBack);

    setSubmitting(true);
    try {
      const result = await api.saveOccupant(tenantId, data);
      toast.success("Occupant uploaded");
      onSuccess(result.occupantUuid);
    } catch (err: any) {
      toast.error(err?.message || "Upload failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label className="text-xs">Name *</Label>
          <Input name="name" required placeholder="Full name" />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Mobile</Label>
          <Input name="mobile" placeholder="10-digit number" />
        </div>
      </div>
      <div className="space-y-1">
        <Label className="text-xs">Address *</Label>
        <Input name="address" required placeholder="Permanent address" />
      </div>
      <div className="space-y-1">
        <Label className="text-xs">Residing Since *</Label>
        <Input name="residentSince" type="date" required max={new Date().toISOString().slice(0, 10)} />
      </div>
      <div className="space-y-1.5">
        <div className="flex items-center gap-3">
          <Label className="text-xs font-medium">Aadhaar *</Label>
          <div className="flex gap-1">
            {(["combined", "split"] as const).map((m) => (
              <Button key={m} type="button" size="sm"
                variant={aadhaarMode === m ? "default" : "outline"}
                className="h-6 px-2 text-xs"
                onClick={() => setAadhaarMode(m)}
              >
                {m === "combined" ? "Combined" : "Front + Back"}
              </Button>
            ))}
          </div>
        </div>
        {aadhaarMode === "combined" ? (
          <Input name="aadhaarcombined" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" />
        ) : (
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Front</Label>
              <Input name="aadhaarfront" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Back</Label>
              <Input name="aadhaarback" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" />
            </div>
          </div>
        )}
      </div>
      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">Employment Proof (optional)</Label>
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Front</Label>
            <Input name="empfront" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" />
          </div>
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Back</Label>
            <Input name="empback" type="file" accept=".pdf,.jpg,.jpeg,.png,.webp" />
          </div>
        </div>
      </div>
      <div className="flex gap-2 pt-1">
        <Button type="submit" className="flex-1" disabled={submitting}>
          {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Upload
        </Button>
        <Button type="button" variant="outline" className="flex-1" disabled={submitting} onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

// ─── Main modal ───────────────────────────────────────────────────────────────

export interface OccupantsModalProps {
  tenant: Tenant | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function OccupantsModal({ tenant, open, onOpenChange }: OccupantsModalProps) {
  const [occupants, setOccupants] = useState<Occupant[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Occupant | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<string>("");
  const [showUpload, setShowUpload] = useState(false);

  const tenantId = tenant?.id ?? 0;

  const loadOccupants = useCallback(async (selectUuid?: string) => {
    if (!tenantId) return;
    setLoading(true);
    try {
      const list = await api.getOccupants(tenantId);
      setOccupants(list);
      if (selectUuid) {
        setSelected(list.find((o) => getUuid(o) === selectUuid) ?? list[0] ?? null);
      } else if (list.length > 0) {
        setSelected((prev) => prev ?? list[0]);
      } else {
        setSelected(null);
      }
    } catch {
      toast.error("Failed to load occupants");
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    if (open && tenantId) {
      setSelected(null);
      setSelectedDoc("");
      setShowUpload(false);
      loadOccupants();
    }
  }, [open, tenantId]);

  useEffect(() => { setSelectedDoc(""); }, [selected]);

  async function handleMarkInactive(o: Occupant) {
    try {
      await api.markOccupantInactive(tenantId, getUuid(o));
      toast.success("Occupant marked inactive");
      loadOccupants(getUuid(o));
    } catch { toast.error("Failed to mark inactive"); }
  }

  async function handleDelete(o: Occupant) {
    const wasSelected = getUuid(o) === getUuid(selected ?? ({} as Occupant));
    try {
      await api.deleteOccupant(tenantId, getUuid(o));
      toast.success("Occupant deleted");
      if (wasSelected) setSelected(null);
      loadOccupants();
    } catch { toast.error("Failed to delete occupant"); }
  }

  const availableDocs = selected
    ? DOC_LABELS.filter((label) => Boolean(getDocFilename(selected, label)))
    : [];

  const documentUrl = selected && selectedDoc
    ? api.getOccupantFileUrl(tenantId, selectedDoc)
    : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[95vw] xl:max-w-[1400px] h-[92vh] p-0 flex flex-col gap-0 overflow-hidden">

        {/* Header */}
        <DialogHeader className="px-6 pt-5 pb-3 shrink-0 border-b">
          <div className="flex items-center justify-between pr-8">
            <DialogTitle className="flex items-center gap-2 text-lg">
              <Users className="h-5 w-5 text-primary" />
              Occupants — {tenant?.name} {tenant?.id}
            </DialogTitle>
            <Button size="sm" variant={showUpload ? "secondary" : "default"} onClick={() => setShowUpload((v) => !v)}>
              {showUpload ? <><X className="mr-2 h-4 w-4" />Cancel Upload</> : <><Upload className="mr-2 h-4 w-4" />Upload KYC</>}
            </Button>
          </div>
        </DialogHeader>

        {/* Upload form */}
        {showUpload && (
          <div className="flex-shrink-0 border-b bg-muted/30 px-6 py-4">
            <UploadForm
              tenantId={tenantId}
              onSuccess={(uuid) => { setShowUpload(false); loadOccupants(uuid); }}
              onCancel={() => setShowUpload(false)}
            />
          </div>
        )}

        {/* Body */}
        <div className="flex flex-1 min-h-0">

          {/* Left pane: occupant list */}
          <div className="w-[380px] lg:w-[420px] flex-shrink-0 border-r flex flex-col">
            <div className="px-4 py-2 border-b bg-muted/20">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {occupants.length} occupant{occupants.length !== 1 ? "s" : ""}
              </p>
            </div>
            {loading ? (
              <div className="flex flex-1 items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : occupants.length === 0 ? (
              <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 text-center text-muted-foreground">
                <Users className="h-8 w-8 opacity-40" />
                <p className="text-sm">No occupants yet.</p>
                <Button size="sm" variant="outline" onClick={() => setShowUpload(true)}>Upload first KYC</Button>
              </div>
            ) : (
              <ScrollArea className="flex-1">
                <div className="p-2 space-y-1">
                  {occupants.map((o) => {
                    const active = o.status === "Active";
                    const isSel = getUuid(o) === getUuid(selected ?? ({} as Occupant));
                    return (
                      <button key={getUuid(o)} onClick={() => setSelected(o)}
                        className={`w-full text-left rounded-lg px-3 py-2.5 transition-colors ${isSel ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0 flex-1">
                            <p className="font-medium text-sm truncate">{o.name || "—"}</p>
                            {o.mobile && (
                              <p className={`text-xs truncate mt-0.5 ${isSel ? "text-primary-foreground/70" : "text-muted-foreground"}`}>{o.mobile}</p>
                            )}
                            {o.address && (
                              <p className={`text-xs line-clamp-1 mt-0.5 ${isSel ? "text-primary-foreground/70" : "text-muted-foreground"}`}>{o.address}</p>
                            )}
                          </div>
                          <Badge className={`text-[10px] flex-shrink-0 ${active ? "bg-green-100 text-green-700 border-green-200" : "bg-slate-100 text-slate-600 border-slate-200"}`}>
                            {active ? "ACTIVE" : "INACTIVE"}
                          </Badge>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </ScrollArea>
            )}
          </div>

          {/* Right pane: detail + document viewer */}
          <div className="flex-1 min-w-0 flex flex-col">
            {!selected ? (
              <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
                Select an occupant to preview their documents.
              </div>
            ) : (
              <>
                {/* Profile bar */}
                <div className="flex-shrink-0 border-b px-5 py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h3 className="text-base font-semibold truncate">{selected.name}</h3>
                      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                        {selected.mobile && <span className="flex items-center gap-1"><Phone className="h-3 w-3" />{selected.mobile}</span>}
                        {selected.address && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{selected.address}</span>}
                        {selected.residentSince && <span className="flex items-center gap-1"><CalendarDays className="h-3 w-3" />Since {formatDate(selected.residentSince)}</span>}
                        {daysStayed(selected.residentSince) && <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{daysStayed(selected.residentSince)}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <Badge className={selected.status === "Active" ? "bg-green-100 text-green-700 border-green-200" : "bg-slate-100 text-slate-600 border-slate-200"}>
                        {selected.status.toUpperCase()}
                      </Badge>
                      {selected.status === "Active" && (
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button size="sm" variant="outline" className="h-7 text-xs">
                              <UserX className="mr-1 h-3.5 w-3.5" />Mark Inactive
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Mark occupant as inactive?</AlertDialogTitle>
                              <AlertDialogDescription>
                                This changes {selected.name}'s status to Inactive. It cannot be reversed from the admin panel.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction onClick={() => handleMarkInactive(selected)}>Confirm</AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      )}
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button size="sm" variant="ghost" className="h-7 text-xs text-destructive hover:text-destructive">
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete occupant?</AlertDialogTitle>
                            <AlertDialogDescription>
                              All KYC documents for {selected.name} will be permanently removed.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90" onClick={() => handleDelete(selected)}>Delete</AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>

                  {/* Document buttons */}
                  {availableDocs.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {availableDocs.map((label) => {
                        const filename = getDocFilename(selected, label);
                        return (
                          <Button key={label} size="sm"
                            variant={selectedDoc === filename ? "default" : "outline"}
                            className="h-7 text-xs"
                            onClick={() => setSelectedDoc((prev) => prev === filename ? "" : filename)}
                          >
                            <FileText className="mr-1.5 h-3.5 w-3.5" />{label}
                          </Button>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Document viewer */}
                <div className="flex-1 min-h-0 bg-muted/20 p-4">
                  {!selectedDoc ? (
                    <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                      {availableDocs.length === 0 ? "No documents uploaded for this occupant." : "Select a document above to preview it."}
                    </div>
                  ) : isPdf(selectedDoc) ? (
                    <iframe src={documentUrl!} title="KYC document" className="h-full min-h-[360px] w-full rounded-lg border bg-white" />
                  ) : (
                    <img src={documentUrl!} alt="KYC document" className="h-full max-h-[60vh] w-full rounded-lg object-contain" />
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
