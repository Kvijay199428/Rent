import { useState, useMemo } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useTenant } from "@/context/TenantContext";
import LoginModal from "@/components/LoginModal";
import BroadcastBanner from "@/components/BroadcastBanner";
import LoadingScreen from "@/components/LoadingScreen";
import { ThemeToggle } from "@/components/theme-toggle";
import { toast } from "sonner";
import { ReceiptRoller } from "@/components/receipts";
import PdfPreviewModal from "@/components/modals/PdfPreviewModal";
import OccupantList from "@/components/OccupantList";
import { DashboardSkeleton } from "@/components/Skeletons";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import PaymentStatusCard from "@/components/PaymentStatusCard";
import ArchiveReceiptCard from "@/components/ArchiveReceiptCard";
import { Receipt as ReceiptIcon, Users, Archive } from "lucide-react";
import { isOlderThan12Months } from "@/lib/utils";
import type { Receipt } from "@/types";

function TenantPortal() {
  const { profile, receipts, occupants, login, logout, isUnlocked, isLoading } = useTenant();
  const [loginError, setLoginError] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [previewBill, setPreviewBill] = useState<string | null>(null);

  const tenant = profile?.tenant;

  const { currentReceipts, archivedReceipts } = useMemo(() => {
    const current: Receipt[] = [];
    const archived: Receipt[] = [];
    receipts.forEach((r) => {
      if (r.Status === "ARCHIVED" || isOlderThan12Months(r.Month)) {
        archived.push(r);
      } else {
        current.push(r);
      }
    });
    current.sort(
      (a, b) => new Date(b.Date || 0).getTime() - new Date(a.Date || 0).getTime()
    );
    archived.sort(
      (a, b) => new Date(b.Date || 0).getTime() - new Date(a.Date || 0).getTime()
    );
    return {
      currentReceipts: current.slice(0, 12),
      archivedReceipts: archived,
    };
  }, [receipts]);

  if (isLoading) {
    return <LoadingScreen isLoading={true} />;
  }

  if (!tenant) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="w-full max-w-md rounded-3xl border bg-card p-8 text-center shadow-sm">
          <h2 className="text-xl font-bold mb-2">Invalid tenant link</h2>
          <p className="text-muted-foreground">
            This portal link is missing, expired, or not mapped to a tenant.
          </p>
        </div>
      </div>
    );
  }

  if (!isUnlocked) {
    return (
      <LoginModal
        tenantName={tenant.name}
        error={loginError}
        loading={isLoggingIn}
        onSubmit={async (pin) => {
          setLoginError("");
          setIsLoggingIn(true);
          try {
            await login(pin);
            toast.success("Portal unlocked");
          } catch (err: any) {
            setLoginError(err?.response?.data?.detail || err?.message || "Login failed");
          } finally {
            setIsLoggingIn(false);
          }
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <BroadcastBanner />
      <header className="sticky top-0 z-10 border-b bg-background/90 backdrop-blur">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold">Welcome, {tenant.name}</h1>
            <p className="text-base text-muted-foreground"><span style={{color:"#708498", fontWeight: 600}}>PROP</span><span style={{color:"#95A58F", fontWeight: 600}}>AURA</span> — Tenant</p>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <button
              onClick={logout}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Lock Portal
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto p-4 md:p-6">
        <Tabs defaultValue="receipts" className="space-y-6">
          <TabsList className="w-full justify-start h-auto gap-1 bg-background border rounded-xl p-1">
            <TabsTrigger
              value="receipts"
              className="gap-1.5 data-[state=active]:bg-muted"
            >
              <ReceiptIcon className="h-3.5 w-3.5" />
              Receipts
              {currentReceipts.length > 0 && (
                <span className="ml-1 text-[10px] font-bold text-muted-foreground">
                  {currentReceipts.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger
              value="occupants"
              className="gap-1.5 data-[state=active]:bg-muted"
            >
              <Users className="h-3.5 w-3.5" />
              Occupants
              {occupants.length > 0 && (
                <span className="ml-1 text-[10px] font-bold text-muted-foreground">
                  {occupants.length}
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger
              value="archive"
              className="gap-1.5 data-[state=active]:bg-muted"
            >
              <Archive className="h-3.5 w-3.5" />
              Archive
              {archivedReceipts.length > 0 && (
                <span className="ml-1 text-[10px] font-bold text-muted-foreground">
                  {archivedReceipts.length}
                </span>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="receipts" className="space-y-6 mt-2">
            <PaymentStatusCard receipts={receipts} />

            <div>
              <h2 className="text-lg font-bold mb-3">Recent Receipts</h2>
              {currentReceipts.length === 0 ? (
                <p className="text-muted-foreground">No receipts found.</p>
              ) : (
                <ReceiptRoller
                  receipts={currentReceipts}
                  onViewPdf={setPreviewBill}
                />
              )}
            </div>
          </TabsContent>

          <TabsContent value="occupants" className="mt-2">
            <OccupantList />
          </TabsContent>

          <TabsContent value="archive" className="space-y-4 mt-2">
            <div>
              <h2 className="text-lg font-bold mb-1">Archived Receipts</h2>
              <p className="text-sm text-muted-foreground">
                Receipts older than 12 months with occupant context.
              </p>
            </div>
            {archivedReceipts.length === 0 ? (
              <p className="text-muted-foreground">
                No archived receipts yet. Older receipts will appear here automatically.
              </p>
            ) : (
              <div className="space-y-4">
                {archivedReceipts.map((r) => (
                  <ArchiveReceiptCard
                    key={r.Bill}
                    receipt={r}
                    occupants={occupants}
                    onViewPdf={setPreviewBill}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      <PdfPreviewModal
        billNo={previewBill ?? ""}
        open={!!previewBill}
        onOpenChange={(open) => {
          if (!open) setPreviewBill(null);
        }}
      />
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/:landlordUuid/t/:tenantId/:viewToken" element={<TenantPortal />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
