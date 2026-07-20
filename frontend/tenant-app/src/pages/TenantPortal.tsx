// File: frontend/tenant-app/src/pages/TenantPortal.tsx
import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import { TENANTROUTES } from "@/lib/routes";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

import { toast } from "sonner";
import {
    Loader2,
    Lock,
    Unlock,
    Receipt,
    Users,
    FileText,
    Download,
    LogOut,
    Eye,
    EyeOff,
    KeyRound,
    Archive,
    Upload,
} from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { ReceiptRoller, ReceiptCard } from "@/components/receipts";
import { OccupantDocumentViewer } from "@/components/OccupantDocumentViewer";
import { OccupantKycUploadDialog } from "@/components/OccupantKycUploadDialog";
import { tenantApi } from "@/lib/api";

// ─── Types ──────────────────────────────────────────────────────────

interface ReceiptData {
    Bill: string;
    Date: string;
    Month: string;
    Tenant: string;
    Previous: number;
    Current: number;
    Units: number;
    Rent: number;
    Additional: number;
    Water: number;
    tankWater: number;
    Electricity: number;
    Total: number;
    PDF: string;
    paymentStatus: string;
    Status?: string;
    MaintenanceCharge: number;
    MaintenanceDesc: string;
    previousArrears: number;
    amountReceived: number;
}

interface Occupant {
    "Occupant UUID": string;
    name: string;
    mobile: string;
    status: string;
    address?: string;
    residentSince?: string;
    aadhaar_front?: string;
    aadhaar_back?: string;
    aadhaar_combined?: string;
    emp_front?: string;
    emp_back?: string;
    uploaddate?: string;
    uploadmonth?: string;
}

interface TENANTPROFILE {
    id: number;
    name: string;
    viewToken: string;
    unlocked: boolean;
}

interface ProfileResponse {
    tenant: TENANTPROFILE;
    receipts?: ReceiptData[];
    occupants?: Occupant[];
}

// ─── Helper: Extract viewToken robustly ───────────────────────────

function useTenantParams(): { tenantId: string | null, viewToken: string | null } {
    const params = useParams();

    // Try common param names (React Router v7 may use camelCase or different naming)
    const possibleNames = ["viewToken", "viewToken", "token", "id"];
    for (const name of possibleNames) {
        const val = params[name];
        if (val && val !== "undefined") return { tenantId: params.tenantId || null, viewToken: val };
    }

    // Fallback: parse from current URL path
    // URL pattern: /rent/t/<token> or /t/<token>
    const path = window.location.pathname;
    const match = path.match(/\/t\/([a-f0-9-]{36})/i);
    if (match) return { tenantId: params.tenantId || null, viewToken: match[1] };

    // Last resort: try to get from the last path segment
    const segments = path.split("/").filter(Boolean);
    const lastSegment = segments[segments.length - 1];
    if (lastSegment && lastSegment.length === 36 && lastSegment.includes("-")) {
        return { tenantId: params.tenantId || null, viewToken: lastSegment };
    }

    console.error("[TenantPortal] Could not extract viewToken from:", { params, path });
    return { tenantId: params.tenantId || null, viewToken: null };
}

function formatCurrency(amount: number): string {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2,
    }).format(amount);
}

type PaymentState = "PENDING" | "PARTIAL" | "PAID" | "ADVANCE";

function getPaymentSummary(receipt?: ReceiptData) {
    if (!receipt) {
        return {
            status: "PENDING" as PaymentState,
            amount: 0,
            label: "No pending bill",
        };
    }

    const total = Number(receipt.Total ?? 0);
    const arrears = Number(receipt.previousArrears ?? 0);
    const received = Number(receipt.amountReceived ?? 0);
    const payable = total + arrears;
    const storedStatus = String(receipt.paymentStatus ?? "").toUpperCase();

    if (storedStatus === "ADVANCE" || received > payable) {
        return {
            status: "ADVANCE" as PaymentState,
            amount: Math.max(0, received - payable),
            label: "Advance credit",
        };
    }

    if (storedStatus === "PARTIAL" || (received > 0 && received < payable)) {
        return {
            status: "PARTIAL" as PaymentState,
            amount: Math.max(0, payable - received),
            label: "Balance due",
        };
    }

    if (storedStatus === "PAID" || received >= payable) {
        return {
            status: "PAID" as PaymentState,
            amount: 0,
            label: "Amount due",
        };
    }

    return {
        status: "PENDING" as PaymentState,
        amount: payable,
        label: "Amount due",
    };
}

function PaymentBadge({ status }: { status: PaymentState }) {
    switch (status) {
        case "PAID": return <Badge className="bg-emerald-500 hover:bg-emerald-600">Paid</Badge>;
        case "PARTIAL": return <Badge className="bg-amber-500 hover:bg-amber-600">Partial</Badge>;
        case "PENDING": return <Badge variant="destructive">Pending</Badge>;
        case "ADVANCE": return <Badge className="bg-cyan-500 hover:bg-cyan-600">Advance</Badge>;
        default: return <Badge variant="outline">{status}</Badge>;
    }
}

// ─── Component ───────────────────────────────────────────────────────

export default function TenantPortal() {
    const { tenantId, viewToken } = useTenantParams();

    // ── Auth / UI State ──
    const [profile, setProfile] = useState<ProfileResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [pin, setPin] = useState("");
    const [showPin, setShowPin] = useState(false);
    const [pinError, setPinError] = useState("");
    const [loggingIn, setLoggingIn] = useState(false);
    const [activeTab, setActiveTab] = useState<"receipts" | "occupants" | "archive">("receipts");
    const [currentPage, setCurrentPage] = useState(1);
    const receiptsPerPage = 6;
    const [publicKey, setPublicKey] = useState<string>("");
    const [kycDialogOpen, setKycDialogOpen] = useState(false);
    const [selectedOccupant, setSelectedOccupant] = useState<Occupant | null>(null);
    const [viewerOpen, setViewerOpen] = useState(false);

    // Fetch public key on mount
    useEffect(() => {
        fetch(TENANTROUTES.TENANTAPIAUTHPUBLICKEY)
            .then(r => r.json())
            .then(d => setPublicKey(d.publicKey))
            .catch(() => toast.error("Failed to load encryption key"));
    }, []);

    // ── Fetch profile (called on mount AND after login) ──
    const fetchProfile = useCallback(async () => {
        if (!viewToken) {
            setLoading(false);
            setProfile(null);
            toast.error("Invalid portal link. Missing access token.");
            return;
        }

        setLoading(true);
        try {
            const res = await fetch(TENANTROUTES.TENANTAPIPROFILEGET(tenantId || 0, viewToken), {
                credentials: "include",
                cache: "no-store",
                headers: {
                    "Cache-Control": "no-cache",
                    Pragma: "no-cache",
                },
            });
            if (!res.ok) {
                if (res.status === 404) {
                    toast.error("Invalid or expired link.");
                } else {
                    toast.error("Failed to load profile.");
                }
                setProfile(null);
                return;
            }
            const data: ProfileResponse = await res.json();
            setProfile(data);
        } catch {
            toast.error("Network error. Please try again.");
        } finally {
            setLoading(false);
        }
    }, [viewToken]);

    // Initial load
    useEffect(() => {
        fetchProfile();
    }, [fetchProfile, viewToken]);

    // ── PIN Login ──
    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!viewToken) {
            setPinError("Invalid portal link.");
            return;
        }

        setPinError("");
        setLoggingIn(true);

        try {
            const { encryptPayload } = await import("@/lib/encryption");
            const encrypted = await encryptPayload({ pin }, publicKey);

            const res = await fetch(TENANTROUTES.TENANTAPIAUTHLOGIN(tenantId || 0, viewToken), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "include",
                body: JSON.stringify(encrypted),
            });

            if (res.ok) {
                const data = await res.json();
                toast.success(data.message || "Unlocked successfully");
                setPin("");
                // 🔑 CRITICAL: Re-fetch profile to get unlocked data with new cookies
                await fetchProfile();
            } else {
                const err = await res.json().catch(() => ({}));
                setPinError(err.detail || "Invalid PIN. Please try again.");
                setPin("");  // Clear on error
            }
        } catch {
            setPinError("Network error. Please try again.");
            setPin("");  // Clear on error
        } finally {
            setLoggingIn(false);
        }
    };

    // ── Logout ──
    const handleLogout = async () => {
        try {
            await fetch(TENANTROUTES.TENANTAPIAUTHLOGOUT(tenantId || 0, viewToken!), {
                method: "POST",
                credentials: "include",
            });
        } catch {
            // ignore
        }
        setProfile(null);
        setActiveTab("receipts");
        setCurrentPage(1);
        await fetchProfile();
        toast.info("Logged out successfully.");
    };

    const handleMarkInactive = async (occupantUuid: string) => {
        try {
            await tenantApi.kyc.markInactive(tenantId!, viewToken!, occupantUuid);
            toast.success("Occupant marked inactive");
            fetchProfile();
        } catch {
            toast.error("Failed to mark inactive");
        }
    };

    // ── Helpers ──
    const isUnlocked = profile?.tenant?.unlocked === true;

    const receipts = profile?.receipts || [];
    const totalPages = Math.max(1, Math.ceil(receipts.length / receiptsPerPage));
    const paginatedReceipts = receipts.slice(
        (currentPage - 1) * receiptsPerPage,
        currentPage * receiptsPerPage
    );

    const getStatusBadge = (status: string) => {
        switch (status) {
            case "PAID":
                return <Badge className="bg-emerald-500 hover:bg-emerald-600">Paid</Badge>;
            case "PARTIAL":
                return <Badge className="bg-amber-500 hover:bg-amber-600">Partial</Badge>;
            case "PENDING":
                return <Badge variant="secondary">Pending</Badge>;
            default:
                return <Badge variant="outline">{status}</Badge>;
        }
    };

    // ── Loading State ──
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-10 w-10 animate-spin text-primary" />
                    <p className="text-muted-foreground">Loading your portal...</p>
                </div>
            </div>
        );
    }

    // ── Error: No viewToken ──
    if (!viewToken) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 p-4">
                <Card className="w-full max-w-md">
                    <CardContent className="pt-6 text-center">
                        <p className="text-destructive font-medium">Invalid portal link.</p>
                        <p className="text-muted-foreground text-sm mt-2">
                            The access token is missing or malformed. Please scan the QR code again or contact your landlord.
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // ── Error: No Profile ──
    if (!profile) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 p-4">
                <Card className="w-full max-w-md">
                    <CardContent className="pt-6 text-center">
                        <p className="text-destructive font-medium">Invalid or expired link.</p>
                        <p className="text-muted-foreground text-sm mt-2">
                            Please scan the QR code again or contact your landlord.
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // ═══════════════════════════════════════════════════════════════════
    //  LOCKED VIEW: Show Login Form ONLY (no data exposed)
    // ═══════════════════════════════════════════════════════════════════
    if (!isUnlocked) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900 p-4">
                <Card className="w-full max-w-md shadow-xl">
                    <CardHeader className="text-center pb-2">
                        <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                            <Lock className="h-8 w-8 text-primary" />
                        </div>
                        <CardTitle className="text-2xl">Tenant Portal</CardTitle>
                        <p className="text-muted-foreground">
                            Welcome, <span className="font-semibold text-foreground">{profile.tenant.name}</span>
                        </p>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleLogin} className="space-y-4">
                            <div>
                                <label className="text-sm font-medium mb-1.5 block">
                                    Enter your 4-digit PIN
                                </label>
                                <div className="relative">
                                    <Input
                                        type={showPin ? "text" : "password"}
                                        inputMode="numeric"
                                        maxLength={4}
                                        value={pin}
                                        onChange={(e) => {
                                            const val = e.target.value.replace(/\D/g, "").slice(0, 4);
                                            setPin(val);
                                            setPinError("");
                                        }}
                                        placeholder="••••"
                                        className="text-center text-2xl tracking-[0.5em] pr-10"
                                        autoFocus
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPin(!showPin)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                    >
                                        {showPin ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                                {pinError && (
                                    <p className="text-destructive text-sm mt-2">{pinError}</p>
                                )}
                            </div>
                            <Button type="submit" className="w-full" disabled={pin.length !== 4 || loggingIn}>
                                {loggingIn ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Verifying...
                                    </>
                                ) : (
                                    <>
                                        <KeyRound className="mr-2 h-4 w-4" />
                                        Unlock Portal
                                    </>
                                )}
                            </Button>
                        </form>
                        <p className="text-xs text-center text-muted-foreground mt-4">
                            Forgot your PIN? Contact your landlord for assistance.
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // ═══════════════════════════════════════════════════════════════════
    //  UNLOCKED VIEW: Full Dashboard (only after successful login)
    // ═══════════════════════════════════════════════════════════════════
    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
            {/* Header */}
            <header className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b sticky top-0 z-50">
                <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
                            <Unlock className="h-5 w-5 text-emerald-500" />
                        </div>
                        <div>
                            <h1 className="font-semibold text-lg leading-tight">
                                {profile.tenant.name}
                                <span className="ml-2 text-sm font-medium text-muted-foreground">
                                    #{profile.tenant.id}
                                </span>
                            </h1>
                            <p className="text-xs text-muted-foreground">Tenant Portal</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Button
                            onClick={() => setKycDialogOpen(true)}
                            className="rounded-full hidden sm:flex"
                            size="sm"
                        >
                            <Upload className="mr-2 h-4 w-4" />
                            Upload KYC
                        </Button>
                        <Button
                            onClick={() => setKycDialogOpen(true)}
                            className="rounded-full sm:hidden"
                            size="icon"
                            title="Upload KYC"
                        >
                            <Upload className="h-4 w-4" />
                        </Button>
                        <ThemeToggle />
                        <Button variant="ghost" size="sm" onClick={handleLogout}>
                            <LogOut className="h-4 w-4 mr-2" />
                            Logout
                        </Button>
                    </div>
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-4 py-6 space-y-6">

                {/* Tabs */}
                <div className="flex gap-2">
                    <Button
                        variant={activeTab === "receipts" ? "default" : "outline"}
                        size="sm"
                        onClick={() => { setActiveTab("receipts"); setCurrentPage(1); }}
                    >
                        <Receipt className="h-4 w-4 mr-2" />
                        Receipts
                    </Button>
                    <Button
                        variant={activeTab === "occupants" ? "default" : "outline"}
                        size="sm"
                        onClick={() => setActiveTab("occupants")}
                    >
                        <Users className="h-4 w-4 mr-2" />
                        Occupants
                    </Button>
                    <Button
                        variant={activeTab === "archive" ? "default" : "outline"}
                        size="sm"
                        onClick={() => setActiveTab("archive")}
                    >
                        <Archive className="h-4 w-4 mr-2" />
                        Archive
                    </Button>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <Card>
                        <CardContent className="pt-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-muted-foreground">Total Receipts</p>
                                    <p className="text-2xl font-bold">{receipts.length}</p>
                                </div>
                                <Receipt className="h-8 w-8 text-primary/60" />
                            </div>
                        </CardContent>
                    </Card>
                    <Card className="rounded-xl shadow-sm">
                        <CardContent className="pt-6">
                            {(() => {
                                const latestReceipt = receipts[0];
                                const payment = getPaymentSummary(latestReceipt);
                                return (
                                    <div className="flex flex-col justify-between h-full">
                                        <div className="flex items-center justify-between">
                                            <span className="text-sm text-muted-foreground">{payment.label}</span>
                                            <PaymentBadge status={payment.status} />
                                        </div>
                                        <div className="mt-2 text-2xl font-bold">
                                            {formatCurrency(payment.amount)}
                                        </div>
                                    </div>
                                );
                            })()}
                        </CardContent>
                    </Card>
                    <Card>
                        <CardContent className="pt-6">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-sm text-muted-foreground">Active Occupants</p>
                                    <p className="text-2xl font-bold">
                                        {(profile.occupants || []).filter(o => String(o.status ?? "Active").toUpperCase() === "ACTIVE").length}
                                    </p>
                                </div>
                                <Users className="h-8 w-8 text-blue-500/60" />
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Receipts Tab */}
                {activeTab === "receipts" && (
                    <div className="space-y-6">
                        {receipts.length === 0 ? (
                            <Card>
                                <CardContent className="pt-6 text-center py-12">
                                    <Receipt className="h-12 w-12 text-muted-foreground/40 mx-auto mb-4" />
                                    <p className="text-muted-foreground">No receipts found.</p>
                                </CardContent>
                            </Card>
                        ) : (
                            <>

                                {/* Pagination */}
                                {totalPages > 1 && (
                                    <div className="flex items-center justify-center gap-2 pt-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                                            disabled={currentPage === 1}
                                        >
                                            Previous
                                        </Button>
                                        <span className="text-sm text-muted-foreground">
                                            Page {currentPage} of {totalPages}
                                        </span>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                                            disabled={currentPage === totalPages}
                                        >
                                            Next
                                        </Button>
                                    </div>
                                )}
                            </>
                        )}
                        <ReceiptRoller receipts={receipts as ReceiptData[]} maxVisible={12} tenantId={tenantId || 0} viewToken={viewToken || ""} />
                    </div>
                )}

                {/* Occupants Tab */}
                {activeTab === "occupants" && (
                    <div className="space-y-4">
                        {(profile.occupants || []).length === 0 ? (
                            <Card>
                                <CardContent className="pt-6 text-center py-12">
                                    <Users className="h-12 w-12 text-muted-foreground/40 mx-auto mb-4" />
                                    <p className="text-muted-foreground">No occupants registered.</p>
                                </CardContent>
                            </Card>
                        ) : (
                            <div className="grid gap-4">
                                {(profile.occupants || []).map((o) => {
                                    const isActive = String(o.status || "Active").toUpperCase() === "ACTIVE";
                                    return (
                                        <Card 
                                            key={o["Occupant UUID"]} 
                                            className="cursor-pointer hover:bg-muted/50 transition-colors"
                                            onClick={() => {
                                                setSelectedOccupant(o);
                                                setViewerOpen(true);
                                            }}
                                        >
                                            <CardContent className="p-4">
                                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                                    <div>
                                                        <div className="flex items-center gap-2">
                                                            <p className="font-semibold">{o.name}</p>
                                                            <Badge variant={isActive ? "default" : "secondary"} className={isActive ? "bg-green-500 hover:bg-green-600" : ""}>
                                                                {o.status || "Active"}
                                                            </Badge>
                                                        </div>
                                                        <p className="text-sm text-muted-foreground mt-1">
                                                            {o.mobile} &middot; {o.address || "No address"}
                                                        </p>
                                                    </div>
                                                    <div className="text-sm text-muted-foreground sm:text-right">
                                                        {o.residentSince && <p>Since: {new Date(`${o.residentSince}T00:00:00`).toLocaleDateString("en-IN")}</p>}
                                                        <p>Added: {o.uploaddate ? new Date(`${o.uploaddate}Z`).toLocaleDateString("en-IN") : "Unknown"}</p>
                                                    </div>
                                                </div>
                                            </CardContent>
                                        </Card>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                )}

                {/* Archive Tab */}
                {activeTab === "archive" && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base flex items-center gap-2">
                                <Archive className="h-4 w-4" />
                                Archived Receipts
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {receipts.filter(r => r.Status === "ARCHIVED").length === 0 ? (
                                <p className="text-muted-foreground text-sm">No archived receipts yet.</p>
                            ) : (
                                <div className="space-y-2">
                                    {receipts
                                        .filter(r => r.Status === "ARCHIVED")
                                        .map(receipt => (
                                            <ReceiptCard
                                                key={receipt.Bill}
                                                receipt={receipt}
                                                variant="archive"
                                                tenantId={tenantId || 0}
                                                viewToken={viewToken || ""}
                                            />
                                        ))}
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}
            </main>

            {kycDialogOpen && (
                <OccupantKycUploadDialog
                    tenantId={tenantId!}
                    viewToken={viewToken!}
                    open={kycDialogOpen}
                    onOpenChange={setKycDialogOpen}
                    onSuccess={() => {
                        setKycDialogOpen(false);
                        fetchProfile();
                    }}
                />
            )}

            {viewerOpen && selectedOccupant && (
                <OccupantDocumentViewer
                    tenantId={tenantId!}
                    viewToken={viewToken!}
                    occupant={selectedOccupant}
                    open={viewerOpen}
                    onOpenChange={setViewerOpen}
                    onMarkInactive={handleMarkInactive}
                />
            )}
        </div>
    );
}