import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router";
import Layout from "../components/Layout";
import { fetchApi } from "../api/client";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";

interface Landlord {
  id: number;
  landlord_uuid: string;
  full_name: string;
  email: string;
  phone: string;
  username: string;
  status: string;
  created_at: string;
  updated_at: string;
  has_totp: boolean;
  failed_attempts: number;
  locked_until: string | null;
  requires_password_change: boolean;
  privacy_consented: boolean;
  privacy_version: string | null;
  privacy_accepted_at: string | null;
  terms_consented: boolean;
  terms_version: string | null;
  terms_accepted_at: string | null;
  tenant_count: number;
  receipt_count: number;
  kyc_count: number;
}

interface ModalData {
  type: "totp" | "password" | "reset" | "reset_whatsapp";
  landlord: Landlord;
  result?: { password?: string; secret?: string; qr_code_base64?: string; message?: string; updated_at?: string; whatsapp_url?: string; requires_password_change?: boolean };
  error?: string;
  loading: boolean;
}

function Pill({ tone, title, children }: { tone: "green" | "amber" | "red" | "gray"; title?: string; children: React.ReactNode }) {
  const tones = {
    green: "bg-green-100 text-green-700",
    amber: "bg-amber-100 text-amber-700",
    red: "bg-red-100 text-red-600",
    gray: "bg-gray-100 text-gray-500",
  };
  return (
    <span
      title={title}
      className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${tones[tone]} ${title ? "cursor-help" : ""}`}
    >
      {children}
    </span>
  );
}

const STATUS_TONE: Record<string, "green" | "amber" | "red" | "gray"> = {
  Active: "green",
  Locked: "red",
  Inactive: "gray",
};

const COL_HEADERS = ["ID", "Name", "Username", "Status", "Privacy", "Terms", "TOTP", "PW Reset", "Tenants", "Receipts", "KYC", "Joined", "Actions"];

export default function LandlordsPage() {
  const [landlords, setLandlords] = useState<Landlord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [modal, setModal] = useState<ModalData | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (statusFilter && statusFilter !== "all") params.set("status", statusFilter);
      params.set("limit", "50");
      const res = await fetchApi(`/landlords?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setLandlords(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load landlords");
    } finally {
      setLoading(false);
    }
  }, [search, statusFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);

  async function toggleTOTP(l: Landlord) {
    setModal({ type: "totp", landlord: l, loading: true });
    try {
      const res = await fetchApi(`/landlords/${l.id}/totp-toggle`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed");
      setModal({ type: "totp", landlord: l, result: data, loading: false });
      fetchData();
    } catch (e: unknown) {
      setModal({ type: "totp", landlord: l, error: e instanceof Error ? e.message : "Failed", loading: false });
    }
  }

  async function revealPassword(l: Landlord) {
    setModal({ type: "password", landlord: l, loading: true });
    try {
      const res = await fetchApi(`/landlords/${l.id}/reveal-password`);
      const data = await res.json();
      if (!res.ok) {
        // Password not in vault — offer reset
        setModal({ type: "password", landlord: l, error: data.detail ?? "Password not available. Use Reset instead.", loading: false });
        return;
      }
      setModal({ type: "password", landlord: l, result: data, loading: false });
    } catch (e: unknown) {
      setModal({ type: "password", landlord: l, error: e instanceof Error ? e.message : "Failed", loading: false });
    }
  }

  async function resetPassword(l: Landlord) {
    if (!confirm(`Reset password for ${l.username}? The new password will be shown once.`)) return;
    setModal({ type: "reset", landlord: l, loading: true });
    try {
      const res = await fetchApi(`/landlords/${l.id}/reset-password`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed");
      setModal({ type: "reset", landlord: l, result: data, loading: false });
    } catch (e: unknown) {
      setModal({ type: "reset", landlord: l, error: e instanceof Error ? e.message : "Failed", loading: false });
    }
  }

  async function resetWithWhatsApp(l: Landlord) {
    if (!l.phone) {
      setModal({ type: "reset_whatsapp", landlord: l, error: "No phone number on file. Add one first.", loading: false });
      return;
    }
    setModal({ type: "reset_whatsapp", landlord: l, loading: true });
    try {
      const res = await fetchApi(`/landlords/${l.id}/reset-password`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Failed");
      setModal({ type: "reset_whatsapp", landlord: l, result: data, loading: false });
    } catch (e: unknown) {
      setModal({ type: "reset_whatsapp", landlord: l, error: e instanceof Error ? e.message : "Failed", loading: false });
    }
  }

  return (
    <Layout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="m-0 text-[26px] font-bold text-[#1a1d2e]">Landlords</h1>
      </div>

      <Card className="mb-5 flex flex-wrap items-center gap-3 rounded-2xl p-4 shadow-[0_2px_12px_rgba(0,0,0,0.07)]">
        <Input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name, username, or email…"
          className="min-w-[200px] flex-1"
        />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-auto">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="Active">Active</SelectItem>
            <SelectItem value="Locked">Locked</SelectItem>
            <SelectItem value="Inactive">Inactive</SelectItem>
          </SelectContent>
        </Select>
      </Card>

      {error && (
        <div className="mb-5 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-gray-400">Loading…</p>
      ) : (
        <Card className="overflow-hidden rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.07)]">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50 hover:bg-slate-50">
                  {COL_HEADERS.map((h) => (
                    <TableHead key={h} className="whitespace-nowrap px-3 py-3 text-[13px] font-semibold text-gray-700">
                      {h}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {landlords.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={COL_HEADERS.length} className="px-3 py-8 text-center text-gray-400">
                      No landlords found.
                    </TableCell>
                  </TableRow>
                )}
                {landlords.map((l) => (
                  <TableRow key={l.id} className="border-b border-gray-100">
                    <TableCell className="px-3 py-3 text-gray-500">{l.id}</TableCell>
                    <TableCell className="px-3 py-3 font-semibold text-[#1a1d2e]">
                      <Link to={`/landlords/${l.id}`} className="text-[#3b4a6b] no-underline hover:underline">
                        {l.full_name || "—"}
                      </Link>
                      {l.email && <div className="text-xs font-normal text-gray-400">{l.email}</div>}
                    </TableCell>
                    <TableCell className="px-3 py-3">
                      <code className="rounded-md bg-slate-100 px-2 py-0.5 text-[13px]">{l.username}</code>
                    </TableCell>
                    <TableCell className="px-3 py-3">
                      <Pill tone={STATUS_TONE[l.status] ?? "gray"}>{l.status}</Pill>
                    </TableCell>
                    <TableCell className="px-3 py-3">
                      {l.privacy_consented ? (
                        <Pill
                          tone="green"
                          title={[
                            "Privacy Policy accepted",
                            l.privacy_version ? `Version ${l.privacy_version}` : null,
                            l.privacy_accepted_at ? `Accepted ${new Date(l.privacy_accepted_at).toLocaleString()}` : null,
                          ].filter(Boolean).join(" · ")}
                        >
                          Accepted
                        </Pill>
                      ) : (
                        <Pill tone="amber" title="Privacy Policy not yet accepted">Pending</Pill>
                      )}
                    </TableCell>
                    <TableCell className="px-3 py-3">
                      {l.terms_consented ? (
                        <Pill
                          tone="green"
                          title={[
                            "Terms and Conditions accepted",
                            l.terms_version ? `Version ${l.terms_version}` : null,
                            l.terms_accepted_at ? `Accepted ${new Date(l.terms_accepted_at).toLocaleString()}` : null,
                          ].filter(Boolean).join(" · ")}
                        >
                          Accepted
                        </Pill>
                      ) : (
                        <Pill tone="amber" title="Terms and Conditions not yet accepted">Pending</Pill>
                      )}
                    </TableCell>
                    <TableCell className="px-3 py-3 text-[13px]">
                      {l.has_totp ? "✅" : "—"}
                    </TableCell>
                    <TableCell className="px-3 py-3 text-center">
                      {l.requires_password_change ? (
                        <Pill tone="amber">PW Pending</Pill>
                      ) : "—"}
                    </TableCell>
                    <TableCell className="px-3 py-3 text-center">{l.tenant_count}</TableCell>
                    <TableCell className="px-3 py-3 text-center">{l.receipt_count}</TableCell>
                    <TableCell className="px-3 py-3 text-center">{l.kyc_count}</TableCell>
                    <TableCell className="whitespace-nowrap px-3 py-3 text-xs text-gray-400">
                      {l.created_at ? new Date(l.created_at).toLocaleDateString() : "—"}
                    </TableCell>
                    <TableCell className="px-3 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        <Button
                          size="sm"
                          onClick={() => toggleTOTP(l)}
                          className={`h-7 px-2.5 text-[11px] font-semibold ${
                            l.has_totp
                              ? "bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
                              : "bg-green-100 text-green-700 hover:bg-green-200"
                          }`}
                        >
                          {l.has_totp ? "Disable TOTP" : "Enable TOTP"}
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => revealPassword(l)}
                          className="h-7 bg-indigo-100 px-2.5 text-[11px] font-semibold text-indigo-800 hover:bg-indigo-200"
                        >
                          Show PW
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => resetPassword(l)}
                          className="h-7 bg-red-100 px-2.5 text-[11px] font-semibold text-red-600 hover:bg-red-200"
                        >
                          Reset PW
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => resetWithWhatsApp(l)}
                          title="Reset password and send via WhatsApp"
                          className="h-7 bg-green-100 px-2.5 text-[11px] font-semibold text-green-700 hover:bg-green-200"
                        >
                          Send WA
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </Card>
      )}

      {/* Modal */}
      {modal && (
        <Dialog open onOpenChange={(open) => { if (!open) setModal(null); }}>
          <DialogContent className="max-h-[80vh] max-w-[440px] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-[17px] font-bold text-[#1a1d2e]">
                {modal.type === "totp" && (modal.landlord.has_totp ? "Disable TOTP" : "Enable TOTP")}
                {modal.type === "password" && "Reveal Password"}
                {modal.type === "reset" && "Reset Password"}
                {modal.type === "reset_whatsapp" && "Reset & Send via WhatsApp"}
                <span className="text-sm font-normal text-gray-500"> — {modal.landlord.username}</span>
              </DialogTitle>
            </DialogHeader>

            {modal.loading && <p className="text-gray-400">Loading…</p>}

            {modal.error && (
              <div className="mb-3 rounded-lg bg-red-50 px-3.5 py-2.5 text-[13px] text-red-600">
                {modal.error}
              </div>
            )}

            {modal.result && (
              <div>
                {modal.type === "totp" && (
                  <div className="text-center">
                    {modal.result.qr_code_base64 && (
                      <>
                        <p className="mb-2 text-[13px] text-gray-700">Scan this QR code with the landlord's authenticator app:</p>
                        <img
                          src={`data:image/png;base64,${modal.result.qr_code_base64}`}
                          alt="TOTP QR"
                          className="mb-3 h-[200px] w-[200px] rounded-lg border border-gray-200"
                        />
                      </>
                    )}
                    {modal.result.secret && (
                      <div className="rounded-lg bg-slate-100 px-3.5 py-2.5 text-[13px] font-mono">
                        Secret: {modal.result.secret}
                      </div>
                    )}
                    {modal.result.message && (
                      <p className="mt-2 text-[13px] text-green-600">{modal.result.message}</p>
                    )}
                  </div>
                )}

                {(modal.type === "password" || modal.type === "reset") && modal.result.password && (
                  <div>
                    <p className="mb-2 text-[13px] text-gray-700">
                      {modal.type === "reset" ? "New password (copy now — shown only once):" : "Current password:"}
                    </p>
                    <div className="flex items-center justify-between rounded-lg bg-slate-100 px-4 py-3 font-mono text-base font-bold text-[#1a1d2e]">
                      <span>{modal.result.password}</span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigator.clipboard.writeText(modal.result!.password!)}
                      >
                        Copy
                      </Button>
                    </div>
                    {modal.result.updated_at && (
                      <p className="mt-2 text-xs text-gray-400">
                        Last updated: {new Date(modal.result.updated_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                )}

                {modal.type === "reset_whatsapp" && modal.result && (
                  <div>
                    {modal.result.password && (
                      <>
                        <p className="mb-2 text-[13px] text-gray-700">
                          New password (copy now — shown only once):
                        </p>
                        <div className="flex items-center justify-between rounded-lg bg-slate-100 px-4 py-3 font-mono text-base font-bold text-[#1a1d2e]">
                          <span>{modal.result.password}</span>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => navigator.clipboard.writeText(modal.result!.password!)}
                          >
                            Copy
                          </Button>
                        </div>
                      </>
                    )}

                    {modal.result.whatsapp_url ? (
                      <div className="mt-4">
                        <p className="mb-2 text-[13px] text-gray-700">
                          Open WhatsApp to send the credentials:
                        </p>
                        <a
                          href={modal.result.whatsapp_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 rounded-lg bg-[#25D366] px-5 py-2.5 text-sm font-semibold text-white no-underline hover:bg-[#1eb958]"
                        >
                          Open WhatsApp
                        </a>
                      </div>
                    ) : (
                      <p className="mt-3 text-[13px] text-gray-400">
                        No phone number on file — WhatsApp URL not generated.
                      </p>
                    )}

                    {modal.result.requires_password_change && (
                      <p className="mt-3 rounded-md bg-amber-100 px-3 py-2 text-xs text-amber-700">
                        The landlord will be required to change their password on next login.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            <Button
              variant="outline"
              onClick={() => setModal(null)}
              className="mt-5 w-full text-sm font-semibold"
            >
              Close
            </Button>
          </DialogContent>
        </Dialog>
      )}
    </Layout>
  );
}