import React, { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText } from "lucide-react";
import { tenantApi } from "@/lib/api";

export interface Occupant {
  "Occupant UUID"?: string;
  occupantuuid?: string;
  name?: string;
  mobile?: string;
  address?: string;
  residentSince?: string;
  status?: string;
  aadhaarfront?: string;
  aadhaarback?: string;
  aadhaarcombined?: string;
  empfront?: string;
  empback?: string;
}

export interface OccupantDocumentViewerProps {
  tenantId: string | number;
  viewToken: string;
  occupant: Occupant | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onMarkInactive: (occupantUuid: string) => void;
}

function daysStayed(residentSince?: string) {
  if (!residentSince) return null;
  const start = new Date(`${residentSince}T00:00:00`);
  if (Number.isNaN(start.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.max(0, Math.floor((today.getTime() - start.getTime()) / 86_400_000));
}

function getDocumentItems(occupant: Occupant) {
  return [
    ["Aadhaar Combined", occupant.aadhaarcombined],
    ["Aadhaar Front", occupant.aadhaarfront],
    ["Aadhaar Back", occupant.aadhaarback],
    ["Employment Proof Front", occupant.empfront],
    ["Employment Proof Back", occupant.empback],
  ].filter(([, filename]) => Boolean(filename)) as Array<[string, string]>;
}

function isPdf(filename: string) {
  return filename.toLowerCase().endsWith(".pdf");
}

export function OccupantDocumentViewer({
  tenantId,
  viewToken,
  occupant,
  open,
  onOpenChange,
  onMarkInactive,
}: OccupantDocumentViewerProps) {
  const [selectedDocument, setSelectedDocument] = useState<string | null>(null);

  // Initialize selected document when dialog opens
  React.useEffect(() => {
    if (open && occupant) {
      const docs = getDocumentItems(occupant);
      if (docs.length > 0) {
        setSelectedDocument(docs[0][1]);
      } else {
        setSelectedDocument(null);
      }
    }
  }, [open, occupant]);

  if (!occupant) return null;

  const isActive = String(occupant.status || "Active").toUpperCase() === "ACTIVE";
  const stayed = daysStayed(occupant.residentSince);
  const uuid = occupant["Occupant UUID"] || occupant.occupantuuid || "";
  const documents = getDocumentItems(occupant);

  const documentUrl = selectedDocument
    ? tenantApi.kyc.getFile(tenantId, viewToken, selectedDocument)
    : undefined;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[95vw] xl:max-w-6xl">
        <DialogHeader>
          <DialogTitle>{occupant.name}</DialogTitle>
          <DialogDescription>
            {occupant.mobile || "No mobile"} &middot; {occupant.address || "No address"}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-5 lg:grid-cols-[280px_1fr]">
          <aside className="space-y-4">
            <div>
              <Badge className={isActive ? "bg-green-100 text-green-700 hover:bg-green-100" : "bg-slate-100 text-slate-700 hover:bg-slate-100"}>
                {isActive ? "ACTIVE" : "INACTIVE"}
              </Badge>
            </div>

            <div className="text-sm space-y-1">
              <p>Residing since: {occupant.residentSince ? new Date(`${occupant.residentSince}T00:00:00`).toLocaleDateString("en-IN") : "—"}</p>
              <p>{stayed === null ? "—" : `${stayed} days stayed`}</p>
            </div>

            <div className="space-y-2">
              {documents.map(([label, filename]) => (
                <Button
                  key={filename}
                  variant={selectedDocument === filename ? "default" : "outline"}
                  className="w-full justify-start"
                  onClick={() => setSelectedDocument(filename)}
                >
                  <FileText className="mr-2 h-4 w-4" />
                  {label}
                </Button>
              ))}
            </div>

            {isActive && (
              <Button
                variant="destructive"
                className="w-full mt-4"
                onClick={() => {
                  onMarkInactive(uuid);
                  onOpenChange(false);
                }}
              >
                Mark inactive
              </Button>
            )}
          </aside>

          <section className="min-h-[55vh] overflow-hidden rounded-xl border bg-muted/30 relative">
            {selectedDocument && documentUrl ? (
              isPdf(selectedDocument) ? (
                <iframe
                  className="h-full min-h-[55vh] w-full border-0"
                  src={documentUrl}
                  title="Occupant KYC document"
                />
              ) : (
                <div className="flex h-full min-h-[55vh] items-center justify-center p-4">
                  <img
                    className="max-h-[55vh] max-w-full object-contain"
                    src={documentUrl}
                    alt="Occupant KYC document"
                  />
                </div>
              )
            ) : (
              <div className="flex h-full min-h-[55vh] items-center justify-center text-sm text-muted-foreground">
                Select a document to preview
              </div>
            )}
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
