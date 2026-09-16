import { useEffect, useState, useCallback } from "react";
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

type Tab = "tenants" | "receipts" | "kyc";

interface Landlord {
  id: number;
  full_name: string;
  username: string;
}

interface PageResult {
  items: Record<string, unknown>[];
  total: number;
  limit: number;
  offset: number;
}

interface TenantAuth {
  tenant_id: number;
  name: string;
  status: string;
  failed_attempts: number;
  locked_until: string | null;
  has_pin: boolean;
  pin: string | null;
  pin_updated_at?: string;
}

const TABS: { key: Tab; label: string; icon: string }[] = [
  { key: "tenants", label: "Tenants", icon: "👤" },
  { key: "receipts", label: "Receipts", icon: "🧾" },
  { key: "kyc", label: "KYC Files", icon: "📄" },
];

const TH_CLS = "bg-[#f9fafb] text-[13px] font-semibold text-gray-700";
const TD_CLS = "text-[#1a1d2e]";

function TenantsTable({ items, onAuth }: { items: Record<string, unknown>[]; onAuth: (id: number) => void }) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-[#f9fafb]">
          {["ID", "Name", "Unit", "Status", "Rent", "Landlord", "Auth"].map((h) => (
            <TableHead key={h} className={TH_CLS}>{h}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((r) => (
          <TableRow key={Number(r.id)} className="border-b border-gray-100">
            <TableCell className={TD_CLS}>{String(r.id)}</TableCell>
            <TableCell className={`${TD_CLS} font-semibold`}>{String(r.name)}</TableCell>
            <TableCell className={TD_CLS}>{String(r.unit ?? "—")}</TableCell>
            <TableCell className={TD_CLS}>
              <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                r.status === "Active" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"
              }`}>
                {String(r.status)}
              </span>
            </TableCell>
            <TableCell className={TD_CLS}>₱{String(r.rent_amount ?? 0)}</TableCell>
            <TableCell className={TD_CLS}>{String(r.landlord_name ?? "—")}</TableCell>
            <TableCell className={TD_CLS}>
              <Button
                size="sm"
                onClick={() => onAuth(Number(r.id))}
                className="h-7 bg-indigo-100 px-2.5 text-[11px] font-semibold text-indigo-800 hover:bg-indigo-200"
              >
                View PIN
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ReceiptsTable({ items }: { items: Record<string, unknown>[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-[#f9fafb]">
          {["Bill #", "Tenant", "Unit", "Total", "Status", "Date", "Month", "Landlord"].map((h) => (
            <TableHead key={h} className={TH_CLS}>{h}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((r) => (
          <TableRow key={String(r.id)} className="border-b border-gray-100">
            <TableCell className={`${TD_CLS} font-mono text-[13px]`}>{String(r.id)}</TableCell>
            <TableCell className={`${TD_CLS} font-semibold`}>{String(r.tenant_name ?? "—")}</TableCell>
            <TableCell className={TD_CLS}>{String(r.tenant_unit ?? "—")}</TableCell>
            <TableCell className={TD_CLS}>₱{String(r.total ?? 0)}</TableCell>
            <TableCell className={TD_CLS}>
              <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                r.paymentstatus === "PAID"
                  ? "bg-green-100 text-green-700"
                  : r.paymentstatus === "PENDING"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-red-100 text-red-600"
              }`}>
                {String(r.paymentstatus)}
              </span>
            </TableCell>
            <TableCell className={TD_CLS}>{r.issued_at ? new Date(String(r.issued_at)).toLocaleDateString() : "—"}</TableCell>
            <TableCell className={TD_CLS}>{String(r.month ?? "—")}</TableCell>
            <TableCell className={TD_CLS}>{String(r.landlord_name ?? "—")}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function KYCTable({ items }: { items: Record<string, unknown>[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-[#f9fafb]">
          {["UUID", "Name", "Status", "Mobile", "Since", "Tenant", "Unit", "Landlord"].map((h) => (
            <TableHead key={h} className={TH_CLS}>{h}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((r) => (
          <TableRow key={String(r.id)} className="border-b border-gray-100">
            <TableCell className="font-mono text-xs text-gray-500">{String(r.id).slice(0, 8)}…</TableCell>
            <TableCell className={`${TD_CLS} font-semibold`}>{String(r.name)}</TableCell>
            <TableCell className={TD_CLS}>
              <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                r.status === "Active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
              }`}>
                {String(r.status ?? "—")}
              </span>
            </TableCell>
            <TableCell className={TD_CLS}>{String(r.mobile ?? "—")}</TableCell>
            <TableCell className={TD_CLS}>{String(r.residentSince ?? "—")}</TableCell>
            <TableCell className={TD_CLS}>{String(r.tenant_name ?? "—")}</TableCell>
            <TableCell className={TD_CLS}>{String(r.tenant_unit ?? "—")}</TableCell>
            <TableCell className={TD_CLS}>{String(r.landlord_name ?? "—")}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export default function DataExplorerPage() {
  const [landlords, setLandlords] = useState<Landlord[]>([]);
  const [selectedLandlord, setSelectedLandlord] = useState<Landlord | null>(null);
  const [landlordSearch, setLandlordSearch] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);
  const [landlordLoadError, setLandlordLoadError] = useState(false);

  const [tab, setTab] = useState<Tab>("tenants");
  const [data, setData] = useState<PageResult>({ items: [], total: 0, limit: 20, offset: 0 });
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(false);

  const [authModal, setAuthModal] = useState<TenantAuth | null>(null);
  const [authLoading, setAuthLoading] = useState(false);

  const loadLandlords = () => {
    fetchApi("/landlords?limit=1000")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        setLandlords(Array.isArray(data) ? data : []);
        setLandlordLoadError(false);
      })
      .catch(() => setLandlordLoadError(true));
  };

  useEffect(() => {
    loadLandlords();
  }, []);

  const filteredLandlords = landlords.filter((l) => {
    if (!landlordSearch) return true;
    const q = landlordSearch.toLowerCase();
    return l.full_name?.toLowerCase().includes(q) || l.username?.toLowerCase().includes(q);
  });

  const fetchData = useCallback(async () => {
    if (!selectedLandlord) { setData({ items: [], total: 0, limit: 20, offset: 0 }); return; }
    setLoading(true);
    const params = new URLSearchParams();
    params.set("landlord_id", String(selectedLandlord.id));
    if (search) params.set("search", search);
    if (statusFilter && statusFilter !== "all") params.set("status", statusFilter);
    params.set("limit", "20");
    params.set("offset", String(data.offset));
    try {
      const res = await fetchApi(`/preview/${tab}?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch {
      setData({ items: [], total: 0, limit: 20, offset: 0 });
    } finally {
      setLoading(false);
    }
  }, [selectedLandlord, tab, search, statusFilter, data.offset]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { setData((d) => ({ ...d, offset: 0 })); }, [tab, search, statusFilter, selectedLandlord]);

  async function showTenantAuth(tenantId: number) {
    setAuthLoading(true);
    setAuthModal(null);
    try {
      const res = await fetchApi(`/preview/tenants/${tenantId}/auth`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setAuthModal(await res.json());
    } catch {
      setAuthModal({ tenant_id: tenantId, name: "Error", status: "?", failed_attempts: 0, locked_until: null, has_pin: false, pin: null });
    } finally {
      setAuthLoading(false);
    }
  }

  return (
    <Layout>
      <h1 className="mb-6 text-[26px] font-bold text-[#1a1d2e]">Data Explorer</h1>

      <Card className="mb-5 rounded-2xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.07)]">
        <label className="mb-1.5 block text-[13px] font-semibold text-gray-700">Select Landlord</label>
        <div className="relative">
          <Input
            type="text"
            value={selectedLandlord ? `${selectedLandlord.full_name} (@${selectedLandlord.username})` : landlordSearch}
            onChange={(e) => {
              setLandlordSearch(e.target.value);
              setSelectedLandlord(null);
              setShowDropdown(true);
            }}
            onFocus={() => setShowDropdown(true)}
            placeholder="Search landlord by name or username…"
          />
          {showDropdown && !selectedLandlord && filteredLandlords.length > 0 && (
            <div className="absolute left-0 right-0 top-full z-50 max-h-60 overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-[0_8px_24px_rgba(0,0,0,0.12)]">
              {filteredLandlords.map((l) => (
                <div
                  key={l.id}
                  onClick={() => { setSelectedLandlord(l); setLandlordSearch(""); setShowDropdown(false); setSearch(""); setStatusFilter("all"); }}
                  className="cursor-pointer border-b border-gray-100 px-3.5 py-2.5 text-sm last:border-0"
                >
                  <div className="font-semibold text-[#1a1d2e]">{l.full_name}</div>
                  <div className="text-xs text-gray-400">@{l.username}</div>
                </div>
              ))}
            </div>
          )}
        </div>
        {landlordLoadError && (
          <p className="mt-2 flex items-center gap-2 text-xs text-amber-600">
            Couldn't load landlords.
            <button type="button" onClick={loadLandlords} className="font-semibold text-amber-700 hover:underline">
              Retry
            </button>
          </p>
        )}
        {selectedLandlord && (
          <button
            onClick={() => { setSelectedLandlord(null); setLandlordSearch(""); }}
            className="mt-2 cursor-pointer rounded-md border border-gray-300 bg-white px-3 py-1 text-xs text-gray-500"
          >
            Clear selection
          </button>
        )}
      </Card>

      {!selectedLandlord && (
        <Card className="rounded-2xl p-12 text-center text-gray-400 shadow-[0_2px_12px_rgba(0,0,0,0.07)]">
          <div className="mb-3 text-4xl">🔍</div>
          <p className="text-[15px]">Select a landlord above to explore their data</p>
        </Card>
      )}

      {selectedLandlord && (
        <>
          <div className="mb-5 flex gap-2">
            {TABS.map((t) => (
              <Button
                key={t.key}
                size="lg"
                onClick={() => setTab(t.key)}
                className={`rounded-lg px-5 ${
                  tab === t.key
                    ? "bg-[#3b4a6b] text-white hover:bg-[#3b4a6b]"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {t.icon} {t.label}
              </Button>
            ))}
          </div>

          <Card className="mb-5 flex flex-wrap items-center gap-3 rounded-2xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.07)]">
            <Input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search…"
              className="min-w-[200px] flex-1"
            />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-auto">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                {tab === "tenants" && (
                  <>
                    <SelectItem value="Active">Active</SelectItem>
                    <SelectItem value="Inactive">Inactive</SelectItem>
                  </>
                )}
                {tab === "receipts" && (
                  <>
                    <SelectItem value="PAID">Paid</SelectItem>
                    <SelectItem value="PENDING">Pending</SelectItem>
                    <SelectItem value="OVERDUE">Overdue</SelectItem>
                  </>
                )}
                {tab === "kyc" && (
                  <>
                    <SelectItem value="Active">Active</SelectItem>
                    <SelectItem value="Inactive">Inactive</SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>
          </Card>

          <Card className="overflow-hidden rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.07)]">
            {loading ? (
              <p className="p-8 text-center text-gray-400">Loading…</p>
            ) : data.items.length === 0 ? (
              <p className="p-8 text-center text-gray-400">No results found for this landlord.</p>
            ) : tab === "tenants" ? (
              <TenantsTable items={data.items} onAuth={showTenantAuth} />
            ) : tab === "receipts" ? (
              <ReceiptsTable items={data.items} />
            ) : (
              <KYCTable items={data.items} />
            )}
          </Card>

          {data.total > data.limit && (
            <div className="mt-5 flex items-center justify-center gap-3">
              <Button
                variant="outline"
                disabled={data.offset === 0}
                onClick={() => setData((d) => ({ ...d, offset: Math.max(0, d.offset - d.limit) }))}
              >
                Previous
              </Button>
              <span className="text-[13px] text-gray-500">
                {data.offset + 1}–{Math.min(data.offset + data.limit, data.total)} of {data.total}
              </span>
              <Button
                variant="outline"
                disabled={data.offset + data.limit >= data.total}
                onClick={() => setData((d) => ({ ...d, offset: d.offset + d.limit }))}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}

      {(authModal || authLoading) && (
        <Dialog open onOpenChange={(open) => { if (!open) { setAuthModal(null); setAuthLoading(false); } }}>
          <DialogContent className="max-h-[80vh] max-w-[400px] overflow-y-auto rounded-2xl">
            <DialogHeader>
              <DialogTitle className="text-[17px] font-bold text-[#1a1d2e]">Tenant Auth Details</DialogTitle>
            </DialogHeader>
            {authLoading && <p className="text-gray-400">Loading…</p>}
            {authModal && !authLoading && (
              <div className="text-sm">
                {[
                  ["Name", authModal.name],
                  ["Status", authModal.status],
                  ["Portal PIN", authModal.pin ?? "Not set"],
                  ["Has PIN", authModal.has_pin ? "Yes" : "No"],
                  ["Failed Attempts", String(authModal.failed_attempts)],
                  ["Locked Until", authModal.locked_until ? new Date(authModal.locked_until).toLocaleString() : "Not locked"],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-baseline gap-3 border-b border-gray-100 py-2.5 last:border-0">
                    <span className="w-[130px] shrink-0 font-semibold text-gray-500">{label}</span>
                    <span className={`break-all text-[#1a1d2e] ${label === "Portal PIN" ? "font-mono" : ""}`}>
                      {String(value)}
                    </span>
                  </div>
                ))}
              </div>
            )}
            <Button
              variant="outline"
              onClick={() => { setAuthModal(null); setAuthLoading(false); }}
              className="mt-4 w-full text-sm font-semibold"
            >
              Close
            </Button>
          </DialogContent>
        </Dialog>
      )}
    </Layout>
  );
}