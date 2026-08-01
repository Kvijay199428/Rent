import { useEffect, useState, useCallback } from "react";
import Layout from "../components/Layout";
import { API_BASE } from "../lib/runtime";

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

const thStyle: React.CSSProperties = {
  padding: "12px 14px", textAlign: "left", fontWeight: 600, color: "#374151",
  borderBottom: "1px solid #e5e7eb", fontSize: 13,
};
const tdStyle: React.CSSProperties = {
  padding: "12px 14px", fontSize: 14, color: "#1a1d2e",
};
const btnSm: React.CSSProperties = {
  padding: "4px 12px", borderRadius: 6, border: "none", cursor: "pointer",
  fontSize: 12, fontWeight: 600,
};

function TenantsTable({ items, onAuth }: { items: Record<string, unknown>[]; onAuth: (id: number) => void }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ background: "#f9fafb" }}>
          <th style={thStyle}>ID</th>
          <th style={thStyle}>Name</th>
          <th style={thStyle}>Unit</th>
          <th style={thStyle}>Status</th>
          <th style={thStyle}>Rent</th>
          <th style={thStyle}>Landlord</th>
          <th style={thStyle}>Auth</th>
        </tr>
      </thead>
      <tbody>
        {items.map((r) => (
          <tr key={Number(r.id)} style={{ borderBottom: "1px solid #f3f4f6" }}>
            <td style={tdStyle}>{String(r.id)}</td>
            <td style={{ ...tdStyle, fontWeight: 600 }}>{String(r.name)}</td>
            <td style={tdStyle}>{String(r.unit ?? "—")}</td>
            <td style={tdStyle}>
              <span style={{
                padding: "2px 10px", borderRadius: 99, fontSize: 12, fontWeight: 600,
                background: r.status === "Active" ? "#dcfce7" : "#fee2e2",
                color: r.status === "Active" ? "#16a34a" : "#dc2626",
              }}>
                {String(r.status)}
              </span>
            </td>
            <td style={tdStyle}>₱{String(r.rent_amount ?? 0)}</td>
            <td style={tdStyle}>{String(r.landlord_name ?? "—")}</td>
            <td style={tdStyle}>
              <button
                onClick={() => onAuth(Number(r.id))}
                style={{ ...btnSm, background: "#e0e7ff", color: "#3730a3" }}
              >
                View PIN
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ReceiptsTable({ items }: { items: Record<string, unknown>[] }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ background: "#f9fafb" }}>
          <th style={thStyle}>Bill #</th>
          <th style={thStyle}>Tenant</th>
          <th style={thStyle}>Unit</th>
          <th style={thStyle}>Total</th>
          <th style={thStyle}>Status</th>
          <th style={thStyle}>Date</th>
          <th style={thStyle}>Month</th>
          <th style={thStyle}>Landlord</th>
        </tr>
      </thead>
      <tbody>
        {items.map((r) => (
          <tr key={String(r.id)} style={{ borderBottom: "1px solid #f3f4f6" }}>
            <td style={{ ...tdStyle, fontFamily: "monospace", fontSize: 13 }}>{String(r.id)}</td>
            <td style={{ ...tdStyle, fontWeight: 600 }}>{String(r.tenant_name ?? "—")}</td>
            <td style={tdStyle}>{String(r.tenant_unit ?? "—")}</td>
            <td style={tdStyle}>₱{String(r.total ?? 0)}</td>
            <td style={tdStyle}>
              <span style={{
                padding: "2px 10px", borderRadius: 99, fontSize: 12, fontWeight: 600,
                background: r.paymentstatus === "PAID" ? "#dcfce7" : r.paymentstatus === "PENDING" ? "#fef9c3" : "#fee2e2",
                color: r.paymentstatus === "PAID" ? "#16a34a" : r.paymentstatus === "PENDING" ? "#92400e" : "#dc2626",
              }}>
                {String(r.paymentstatus)}
              </span>
            </td>
            <td style={tdStyle}>{r.issued_at ? new Date(String(r.issued_at)).toLocaleDateString() : "—"}</td>
            <td style={tdStyle}>{String(r.month ?? "—")}</td>
            <td style={tdStyle}>{String(r.landlord_name ?? "—")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function KYCTable({ items }: { items: Record<string, unknown>[] }) {
  return (
    <table style={{ width: "100%", borderCollapse: "collapse" }}>
      <thead>
        <tr style={{ background: "#f9fafb" }}>
          <th style={thStyle}>UUID</th>
          <th style={thStyle}>Name</th>
          <th style={thStyle}>Status</th>
          <th style={thStyle}>Mobile</th>
          <th style={thStyle}>Since</th>
          <th style={thStyle}>Tenant</th>
          <th style={thStyle}>Unit</th>
          <th style={thStyle}>Landlord</th>
        </tr>
      </thead>
      <tbody>
        {items.map((r) => (
          <tr key={String(r.id)} style={{ borderBottom: "1px solid #f3f4f6" }}>
            <td style={{ ...tdStyle, fontFamily: "monospace", fontSize: 12, color: "#6b7280" }}>{String(r.id).slice(0, 8)}…</td>
            <td style={{ ...tdStyle, fontWeight: 600 }}>{String(r.name)}</td>
            <td style={tdStyle}>
              <span style={{
                padding: "2px 10px", borderRadius: 99, fontSize: 12, fontWeight: 600,
                background: r.status === "Active" ? "#dcfce7" : "#f3f4f6",
                color: r.status === "Active" ? "#16a34a" : "#6b7280",
              }}>
                {String(r.status ?? "—")}
              </span>
            </td>
            <td style={tdStyle}>{String(r.mobile ?? "—")}</td>
            <td style={tdStyle}>{String(r.residentSince ?? "—")}</td>
            <td style={tdStyle}>{String(r.tenant_name ?? "—")}</td>
            <td style={tdStyle}>{String(r.tenant_unit ?? "—")}</td>
            <td style={tdStyle}>{String(r.landlord_name ?? "—")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function DataExplorerPage() {
  const [landlords, setLandlords] = useState<Landlord[]>([]);
  const [selectedLandlord, setSelectedLandlord] = useState<Landlord | null>(null);
  const [landlordSearch, setLandlordSearch] = useState("");
  const [showDropdown, setShowDropdown] = useState(false);

  const [tab, setTab] = useState<Tab>("tenants");
  const [data, setData] = useState<PageResult>({ items: [], total: 0, limit: 20, offset: 0 });
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(false);

  const [authModal, setAuthModal] = useState<TenantAuth | null>(null);
  const [authLoading, setAuthLoading] = useState(false);

  // Fetch landlords for dropdown
  useEffect(() => {
    fetch(`${API_BASE}/landlords?limit=1000`, { credentials: "include" })
      .then((r) => r.json())
      .then((data) => setLandlords(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, []);

  const filteredLandlords = landlords.filter((l) => {
    if (!landlordSearch) return true;
    const q = landlordSearch.toLowerCase();
    return l.full_name?.toLowerCase().includes(q) || l.username?.toLowerCase().includes(q);
  });

  // Fetch preview data
  const fetchData = useCallback(async () => {
    if (!selectedLandlord) { setData({ items: [], total: 0, limit: 20, offset: 0 }); return; }
    setLoading(true);
    const params = new URLSearchParams();
    params.set("landlord_id", String(selectedLandlord.id));
    if (search) params.set("search", search);
    if (statusFilter) params.set("status", statusFilter);
    params.set("limit", "20");
    params.set("offset", String(data.offset));
    try {
      const res = await fetch(`${API_BASE}/preview/${tab}?${params}`, { credentials: "include" });
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
      const res = await fetch(`${API_BASE}/preview/tenants/${tenantId}/auth`, { credentials: "include" });
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
      <h1 style={{ margin: "0 0 24px", fontSize: 26, fontWeight: 700, color: "#1a1d2e" }}>Data Explorer</h1>

      {/* Landlord Selector */}
      <div style={{
        background: "#fff", borderRadius: 14, padding: "16px 20px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.07)", marginBottom: 20,
      }}>
        <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 6 }}>
          Select Landlord
        </label>
        <div style={{ position: "relative" }}>
          <input
            type="text"
            value={selectedLandlord ? `${selectedLandlord.full_name} (@${selectedLandlord.username})` : landlordSearch}
            onChange={(e) => {
              setLandlordSearch(e.target.value);
              setSelectedLandlord(null);
              setShowDropdown(true);
            }}
            onFocus={() => setShowDropdown(true)}
            placeholder="Search landlord by name or username…"
            style={{ width: "100%", padding: "10px 14px", borderRadius: 8, border: "1.5px solid #d1d5db", fontSize: 14, boxSizing: "border-box" }}
          />
          {showDropdown && !selectedLandlord && filteredLandlords.length > 0 && (
            <div style={{
              position: "absolute", top: "100%", left: 0, right: 0, zIndex: 50,
              background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8,
              maxHeight: 240, overflowY: "auto", boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
            }}>
              {filteredLandlords.map((l) => (
                <div
                  key={l.id}
                  onClick={() => { setSelectedLandlord(l); setLandlordSearch(""); setShowDropdown(false); setSearch(""); setStatusFilter(""); }}
                  style={{ padding: "10px 14px", cursor: "pointer", borderBottom: "1px solid #f3f4f6", fontSize: 14 }}
                >
                  <div style={{ fontWeight: 600, color: "#1a1d2e" }}>{l.full_name}</div>
                  <div style={{ fontSize: 12, color: "#9ca3af" }}>@{l.username}</div>
                </div>
              ))}
            </div>
          )}
        </div>
        {selectedLandlord && (
          <button
            onClick={() => { setSelectedLandlord(null); setLandlordSearch(""); }}
            style={{ marginTop: 8, padding: "4px 12px", borderRadius: 6, border: "1px solid #d1d5db", background: "#fff", fontSize: 12, cursor: "pointer", color: "#6b7280" }}
          >
            Clear selection
          </button>
        )}
      </div>

      {!selectedLandlord && (
        <div style={{ background: "#fff", borderRadius: 14, padding: "48px 24px", boxShadow: "0 2px 12px rgba(0,0,0,0.07)", textAlign: "center", color: "#9ca3af" }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
          <p style={{ fontSize: 15 }}>Select a landlord above to explore their data</p>
        </div>
      )}

      {selectedLandlord && (
        <>
          <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                style={{
                  padding: "10px 20px", borderRadius: 8, border: "none", cursor: "pointer", fontSize: 14, fontWeight: 600,
                  background: tab === t.key ? "#3b4a6b" : "#f3f4f6",
                  color: tab === t.key ? "#fff" : "#374151",
                  transition: "all 0.15s",
                }}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </div>

          <div style={{
            background: "#fff", borderRadius: 14, padding: "16px 20px",
            boxShadow: "0 2px 12px rgba(0,0,0,0.07)", marginBottom: 20,
            display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap",
          }}>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search…"
              style={{ flex: 1, minWidth: 200, padding: "10px 14px", borderRadius: 8, border: "1.5px solid #d1d5db", fontSize: 14 }}
            />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ padding: "10px 14px", borderRadius: 8, border: "1.5px solid #d1d5db", fontSize: 14 }}
            >
              <option value="">All statuses</option>
              {tab === "tenants" && (
                <>
                  <option value="Active">Active</option>
                  <option value="Inactive">Inactive</option>
                </>
              )}
              {tab === "receipts" && (
                <>
                  <option value="PAID">Paid</option>
                  <option value="PENDING">Pending</option>
                  <option value="OVERDUE">Overdue</option>
                </>
              )}
              {tab === "kyc" && (
                <>
                  <option value="Active">Active</option>
                  <option value="Inactive">Inactive</option>
                </>
              )}
            </select>
          </div>

          <div style={{ background: "#fff", borderRadius: 14, boxShadow: "0 2px 12px rgba(0,0,0,0.07)", overflow: "hidden" }}>
            {loading ? (
              <p style={{ padding: "32px 16px", textAlign: "center", color: "#9ca3af" }}>Loading…</p>
            ) : data.items.length === 0 ? (
              <p style={{ padding: "32px 16px", textAlign: "center", color: "#9ca3af" }}>No results found for this landlord.</p>
            ) : tab === "tenants" ? (
              <TenantsTable items={data.items} onAuth={showTenantAuth} />
            ) : tab === "receipts" ? (
              <ReceiptsTable items={data.items} />
            ) : (
              <KYCTable items={data.items} />
            )}
          </div>

          {data.total > data.limit && (
            <div style={{ display: "flex", justifyContent: "center", gap: 12, marginTop: 20 }}>
              <button
                disabled={data.offset === 0}
                onClick={() => setData((d) => ({ ...d, offset: Math.max(0, d.offset - d.limit) }))}
                style={{
                  padding: "8px 20px", borderRadius: 8, border: "1.5px solid #d1d5db", background: "#fff",
                  cursor: data.offset === 0 ? "not-allowed" : "pointer", fontSize: 13, fontWeight: 600,
                  opacity: data.offset === 0 ? 0.5 : 1,
                }}
              >
                Previous
              </button>
              <span style={{ padding: "8px 0", fontSize: 13, color: "#6b7280" }}>
                {data.offset + 1}–{Math.min(data.offset + data.limit, data.total)} of {data.total}
              </span>
              <button
                disabled={data.offset + data.limit >= data.total}
                onClick={() => setData((d) => ({ ...d, offset: d.offset + d.limit }))}
                style={{
                  padding: "8px 20px", borderRadius: 8, border: "1.5px solid #d1d5db", background: "#fff",
                  cursor: data.offset + data.limit >= data.total ? "not-allowed" : "pointer", fontSize: 13, fontWeight: 600,
                  opacity: data.offset + data.limit >= data.total ? 0.5 : 1,
                }}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {/* Tenant Auth Modal */}
      {(authModal || authLoading) && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200 }}
          onClick={() => { setAuthModal(null); setAuthLoading(false); }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "#fff", borderRadius: 16, padding: "28px 32px", width: "100%", maxWidth: 400, margin: "0 16px", maxHeight: "80vh", overflowY: "auto",
              boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
            }}
          >
            <h2 style={{ margin: "0 0 16px", fontSize: 17, fontWeight: 700, color: "#1a1d2e" }}>
              Tenant Auth Details
            </h2>
            {authLoading && <p style={{ color: "#9ca3af" }}>Loading…</p>}
            {authModal && !authLoading && (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                <tbody>
                  {[
                    ["Name", authModal.name],
                    ["Status", authModal.status],
                    ["Portal PIN", authModal.pin ?? "Not set"],
                    ["Has PIN", authModal.has_pin ? "Yes" : "No"],
                    ["Failed Attempts", String(authModal.failed_attempts)],
                    ["Locked Until", authModal.locked_until ? new Date(authModal.locked_until).toLocaleString() : "Not locked"],
                  ].map(([label, value]) => (
                    <tr key={label} style={{ borderBottom: "1px solid #f3f4f6" }}>
                      <td style={{ padding: "10px 0", fontWeight: 600, color: "#6b7280", width: 130 }}>{label}</td>
                      <td style={{ padding: "10px 0", color: "#1a1d2e", fontFamily: label === "Portal PIN" ? "monospace" : "inherit" }}>
                        {String(value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <button
              onClick={() => { setAuthModal(null); setAuthLoading(false); }}
              style={{
                marginTop: 20, width: "100%", padding: "10px 0", borderRadius: 8, border: "1.5px solid #d1d5db",
                background: "#fff", fontSize: 14, fontWeight: 600, cursor: "pointer",
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </Layout>
  );
}
