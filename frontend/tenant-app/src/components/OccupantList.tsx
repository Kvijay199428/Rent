import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import OccupantCard from "@/components/OccupantCard";
import { OccupantDocumentViewer } from "@/components/OccupantDocumentViewer";
import { OccupantKycUploadDialog } from "@/components/OccupantKycUploadDialog";
import { useTenant } from "@/context/TenantContext";
import type { Occupant } from "@/types";
import { toast } from "sonner";
import { tenantApi } from "@/lib/api";

export default function OccupantList() {
  const { occupants, readOnly, refetch } = useTenant();
  const [selectedOccupant, setSelectedOccupant] = useState<Occupant | null>(null);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);

  const handleView = (occupant: Occupant) => {
    setSelectedOccupant(occupant);
    setViewerOpen(true);
  };

  const handleMarkInactive = async (occupantUuid: string) => {
    try {
      await tenantApi.kyc.markInactive(occupantUuid);
      toast.success("Occupant marked as inactive");
      refetch();
    } catch {
      toast.error("Failed to mark occupant as inactive");
    }
  };

  return (
    <>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-bold">Occupants</h2>
        <Button size="sm" onClick={() => setUploadOpen(true)} disabled={readOnly}>
          <Plus className="h-4 w-4 mr-1" />
          Add
        </Button>
      </div>

      {occupants.length === 0 ? (
        <p className="text-muted-foreground">No occupants registered.</p>
      ) : (
        <div className="grid md:grid-cols-2 gap-3">
          {occupants.map((o) => (
            <OccupantCard
              key={o["Occupant UUID"] || o.occupantUuid}
              occupant={o}
              onView={handleView}
            />
          ))}
        </div>
      )}

      <OccupantDocumentViewer
        occupant={selectedOccupant}
        open={viewerOpen}
        onOpenChange={setViewerOpen}
        onMarkInactive={handleMarkInactive}
      />

      <OccupantKycUploadDialog
        open={uploadOpen}
        onOpenChange={setUploadOpen}
        onSuccess={() => refetch()}
      />
    </>
  );
}
