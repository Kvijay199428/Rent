import React, { useState, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import {
  User,
  Receipt,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Building2,
  Phone,
  MapPin,
  Wallet,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ─────────────────────────────────────────────────────────

interface TenantProfile {
  Tenant_ID: string;
  Tenant_Name: string;
  Phone: string;
  Email: string;
  Company: string;
  Address: string;
  Room: string;
  Meter_ID: string;
  PIN: string;
  Rent: string;
  Water: string;
  Electricity_Rate: string;
  Additional_Person_Rate: string;
  Tank_Water: string;
  Status: string;
}

interface ReceiptData {
  Bill_No: string;
  Tenant_ID: string;
  Month: string;
  Date: string;
  Previous: string;
  Current: string;
  Units: string;
  Rent: string;
  Water: string;
  Electricity: string;
  Additional: string;
  Tank_Water: string;
  Maintenance: string;
  Arrears: string;
  Amount_Received: string;
  Total: string;
  Payment_Status: string;
  Receipt_Status: string;
}

interface TenantPreview {
  profile: TenantProfile;
  receipts: ReceiptData[];
}

interface FilePreview {
  [tenantId: string]: TenantPreview;
}

interface PreviewResponse {
  status: string;
  files: {
    [filename: string]: FilePreview;
  };
}

interface PreviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  previewData: PreviewResponse | null;
  files: File[];
  onImportSuccess: () => void;
}

// ─── Component ─────────────────────────────────────────────────────

export function PreviewDialog({
  open,
  onOpenChange,
  previewData,
  files,
  onImportSuccess,
}: PreviewDialogProps) {
  const [selectedTenantKey, setSelectedTenantKey] = useState<string | null>(null);
  const [selectedTargets, setSelectedTargets] = useState<Set<string>>(new Set());
  const [isExecuting, setIsExecuting] = useState(false);

  // Flatten all tenants from all files into a single list
  const allTenants = React.useMemo(() => {
    if (!previewData?.files) return [];
    const tenants: {
      key: string;
      filename: string;
      tenantId: string;
      profile: TenantProfile;
      receipts: ReceiptData[];
    }[] = [];

    Object.entries(previewData.files).forEach(([filename, fileData]) => {
      Object.entries(fileData).forEach(([tenantId, tenantData]) => {
        tenants.push({
          key: `${filename}::${tenantId}`,
          filename,
          tenantId,
          profile: tenantData.profile,
          receipts: tenantData.receipts,
        });
      });
    });
    return tenants;
  }, [previewData]);

  // Select first tenant by default when data loads
  React.useEffect(() => {
    if (allTenants.length > 0 && !selectedTenantKey) {
      setSelectedTenantKey(allTenants[0].key);
      setSelectedTargets(new Set(allTenants.map((t) => t.key)));
    }
  }, [allTenants, selectedTenantKey]);

  const selectedTenant = allTenants.find((t) => t.key === selectedTenantKey);

  const toggleSelection = (key: string) => {
    setSelectedTargets((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedTargets.size === allTenants.length) {
      setSelectedTargets(new Set());
    } else {
      setSelectedTargets(new Set(allTenants.map((t) => t.key)));
    }
  };

  // ─── FIXED: Import Execute ─────────────────────────────────────
  const handleExecute = async () => {
    if (selectedTargets.size === 0) {
      toast.error("Please select at least one tenant to import");
      return;
    }

    setIsExecuting(true);
    try {
      const formData = new FormData();
      files.forEach((file) => {
        formData.append("files", file);
      });
      const targetsArray = Array.from(selectedTargets);
      formData.append("selectedtargets", JSON.stringify(targetsArray));

      const basePath = window.location.pathname.startsWith('/rent') ? '/rent' : '';
      const response = await fetch(`${basePath}/admin/api/import-execute`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Import failed: ${response.status}`);
      }

      const result = await response.json();
      toast.success(result.message || "Import completed successfully");
      onOpenChange(false);
      onImportSuccess();
    } catch (err: any) {
      toast.error(err.message || "Import failed");
      console.error("Import execute error:", err);
    } finally {
      setIsExecuting(false);
    }
  };

  if (!previewData || allTenants.length === 0) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Import Preview</DialogTitle>
            <DialogDescription>No data to preview</DialogDescription>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* OPTIMIZED: Full viewport width with proper max-width, increased height */}
      <DialogContent className="max-w-[95vw] xl:max-w-[1400px] h-[92vh] p-0 flex flex-col gap-0 overflow-hidden">
        {/* Header */}
        <DialogHeader className="px-6 pt-5 pb-3 shrink-0 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileSpreadsheet className="h-6 w-6 text-emerald-500 shrink-0" />
              <div>
                <DialogTitle className="text-xl">Import Preview</DialogTitle>
                <DialogDescription className="mt-1 text-sm">
                  Review tenants and receipts before importing.{" "}
                  <span className="font-medium text-foreground">
                    {selectedTargets.size} of {allTenants.length}
                  </span>{" "}
                  selected.
                </DialogDescription>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={toggleAll}
              className="h-8"
            >
              {selectedTargets.size === allTenants.length ? (
                <>Deselect All</>
              ) : (
                <>Select All</>
              )}
            </Button>
          </div>
        </DialogHeader>

        {/* Split Pane Content */}
        <div className="flex-1 min-h-0 flex">
          {/* LEFT PANE: Tenant Cards - OPTIMIZED wider */}
          <div className="w-[380px] lg:w-[420px] border-r bg-muted/30 flex flex-col shrink-0">
            <div className="px-4 py-2.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider shrink-0 border-b bg-muted/50">
              Tenants ({allTenants.length})
            </div>
            <ScrollArea className="flex-1">
              <div className="p-2 space-y-1.5">
                {allTenants.map((tenant) => {
                  const isSelected = selectedTargets.has(tenant.key);
                  const isActive = selectedTenantKey === tenant.key;
                  const profile = tenant.profile;

                  return (
                    <div
                      key={tenant.key}
                      onClick={() => setSelectedTenantKey(tenant.key)}
                      className={cn(
                        "group relative rounded-lg border p-3 cursor-pointer transition-all",
                        "hover:bg-accent hover:border-accent-foreground/20",
                        isActive && "bg-primary/10 border-primary/50 ring-1 ring-primary/30",
                        !isActive && "bg-card border-border"
                      )}
                    >
                      {/* Checkbox */}
                      <div
                        className="absolute top-3 right-3 z-10"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleSelection(tenant.key);
                        }}
                      >
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={() => toggleSelection(tenant.key)}
                        />
                      </div>

                      {/* Profile Content */}
                      <div className="pr-8">
                        <div className="flex items-center gap-2.5 mb-2">
                          <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                            <User className="h-4 w-4 text-primary" />
                          </div>
                          <div className="min-w-0">
                            <p className="font-semibold text-sm truncate leading-tight">
                              {profile.Tenant_Name}
                            </p>
                            <p className="text-xs text-muted-foreground font-medium">
                              {profile.Tenant_ID}
                            </p>
                          </div>
                        </div>

                        <div className="mt-2 space-y-1.5">
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Phone className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
                            <span className="truncate">{profile.Phone || "—"}</span>
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <MapPin className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
                            <span className="truncate">Room {profile.Room || "—"}</span>
                            {profile.Meter_ID && (
                              <span className="text-muted-foreground/50">• {profile.Meter_ID}</span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Wallet className="h-3.5 w-3.5 shrink-0 text-muted-foreground/70" />
                            <span>₹{parseFloat(profile.Rent || "0").toLocaleString("en-IN")}</span>
                            <span className="text-muted-foreground/50">/mo</span>
                          </div>
                        </div>

                        <div className="mt-2.5 flex items-center gap-2">
                          <Badge
                            variant={
                              profile.Status === "Active" ? "default" : "secondary"
                            }
                            className="text-[10px] h-5 px-1.5"
                          >
                            {profile.Status}
                          </Badge>
                          <Badge
                            variant="outline"
                            className="text-[10px] h-5 px-1.5 gap-1"
                          >
                            <Receipt className="h-3 w-3" />
                            {tenant.receipts.length} receipt{tenant.receipts.length !== 1 ? "s" : ""}
                          </Badge>
                        </div>
                      </div>

                      {/* Active indicator */}
                      {isActive && (
                        <div className="absolute left-0 top-3 bottom-3 w-0.5 bg-primary rounded-r-full" />
                      )}
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          </div>

          {/* RIGHT PANE: Receipts Table - OPTIMIZED */}
          <div className="flex-1 flex flex-col min-w-0 bg-background">
            {selectedTenant ? (
              <>
                {/* Tenant Header - Compact */}
                <div className="px-5 py-3 border-b bg-muted/20 shrink-0">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                        <Building2 className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <h3 className="font-semibold text-base">
                          {selectedTenant.profile.Tenant_Name}
                        </h3>
                        <p className="text-xs text-muted-foreground">
                          {selectedTenant.receipts.length} receipt
                          {selectedTenant.receipts.length !== 1 ? "s" : ""} to import
                          {selectedTenant.profile.Room && ` • Room ${selectedTenant.profile.Room}`}
                          {selectedTenant.profile.Phone && ` • ${selectedTenant.profile.Phone}`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                      {selectedTenant.profile.Status}
                    </div>
                  </div>
                </div>

                {/* Receipts Table - Scrollable */}
                <ScrollArea className="flex-1">
                  {selectedTenant.receipts.length > 0 ? (
                    <div className="p-4">
                      <Table>
                        <TableHeader className="bg-muted/50 sticky top-0">
                          <TableRow>
                            <TableHead className="w-[90px] text-xs">Bill No</TableHead>
                            <TableHead className="text-xs">Month</TableHead>
                            <TableHead className="text-xs">Date</TableHead>
                            <TableHead className="text-right text-xs">Units</TableHead>
                            <TableHead className="text-right text-xs">Rent</TableHead>
                            <TableHead className="text-right text-xs">Electricity</TableHead>
                            <TableHead className="text-right text-xs">Water</TableHead>
                            <TableHead className="text-right text-xs">Total</TableHead>
                            <TableHead className="text-xs">Status</TableHead>
                            <TableHead className="text-xs">Payment</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {selectedTenant.receipts.map((receipt, idx) => (
                            <TableRow key={idx}>
                              <TableCell className="font-medium text-xs py-2">
                                {receipt.Bill_No}
                              </TableCell>
                              <TableCell className="text-xs py-2">{receipt.Month}</TableCell>
                              <TableCell className="text-xs py-2 whitespace-nowrap">{receipt.Date}</TableCell>
                              <TableCell className="text-right text-xs py-2 tabular-nums">{receipt.Units}</TableCell>
                              <TableCell className="text-right text-xs py-2 tabular-nums">
                                ₹{parseFloat(receipt.Rent || "0").toLocaleString("en-IN")}
                              </TableCell>
                              <TableCell className="text-right text-xs py-2 tabular-nums">
                                ₹{parseFloat(receipt.Electricity || "0").toLocaleString("en-IN")}
                              </TableCell>
                              <TableCell className="text-right text-xs py-2 tabular-nums">
                                ₹{parseFloat(receipt.Water || "0").toLocaleString("en-IN")}
                              </TableCell>
                              <TableCell className="text-right font-semibold text-xs py-2 tabular-nums">
                                ₹{parseFloat(receipt.Total || "0").toLocaleString("en-IN")}
                              </TableCell>
                              <TableCell className="py-2">
                                <Badge
                                  variant={
                                    receipt.Receipt_Status === "ACTIVE"
                                      ? "default"
                                      : "secondary"
                                  }
                                  className="text-[10px] h-5"
                                >
                                  {receipt.Receipt_Status}
                                </Badge>
                              </TableCell>
                              <TableCell className="py-2">
                                <Badge
                                  variant={
                                    receipt.Payment_Status === "PAID"
                                      ? "default"
                                      : receipt.Payment_Status === "PENDING"
                                      ? "destructive"
                                      : "outline"
                                  }
                                  className="text-[10px] h-5"
                                >
                                  {receipt.Payment_Status}
                                </Badge>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-64 text-muted-foreground">
                      <Receipt className="h-10 w-10 mb-3 opacity-40" />
                      <p className="text-sm">No receipts for this tenant</p>
                    </div>
                  )}
                </ScrollArea>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                <AlertCircle className="h-10 w-10 mb-3 opacity-40" />
                <p className="text-sm">Select a tenant to preview receipts</p>
              </div>
            )}
          </div>
        </div>

        <Separator />

        {/* Footer */}
        <DialogFooter className="px-6 py-4 shrink-0">
          <div className="flex items-center gap-3 w-full justify-between">
            <p className="text-xs text-muted-foreground">
              {selectedTargets.size} tenant{selectedTargets.size !== 1 ? "s" : ""} selected for import
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isExecuting}
              >
                Cancel
              </Button>
              <Button
                onClick={handleExecute}
                disabled={isExecuting || selectedTargets.size === 0}
                className="min-w-[140px]"
              >
                {isExecuting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Import {selectedTargets.size > 0 && `(${selectedTargets.size})`}
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default PreviewDialog;