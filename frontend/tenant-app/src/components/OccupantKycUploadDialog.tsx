import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { tenantApi } from "@/lib/api";

export interface OccupantKycUploadDialogProps {
  tenantId: string | number;
  viewToken: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function OccupantKycUploadDialog({
  tenantId,
  viewToken,
  open,
  onOpenChange,
  onSuccess,
}: OccupantKycUploadDialogProps) {
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

    // Build a clean FormData with only non-empty file fields so the backend
    // validation isn't tripped by empty browser file inputs from the hidden mode
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
      await tenantApi.kyc.upload(tenantId, viewToken, data);
      toast.success("Occupant uploaded");
      onSuccess();
      onOpenChange(false);
    } catch (err: any) {
      toast.error(err?.message || "Upload failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Upload Occupant KYC</DialogTitle>
          <DialogDescription>
            Add a new occupant by providing their details and ID documents.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
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
            <Input name="residentSince" type="date" required max={new Date().toISOString().split('T')[0]} />
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <Label className="text-xs font-medium">Aadhaar *</Label>
              <div className="flex gap-1">
                {(["combined", "split"] as const).map((m) => (
                  <Button
                    key={m}
                    type="button"
                    size="sm"
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
          
          <div className="space-y-2">
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
          
          <div className="flex gap-2 pt-2">
            <Button type="submit" className="flex-1" disabled={submitting}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Upload
            </Button>
            <Button type="button" variant="outline" className="flex-1" disabled={submitting} onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
