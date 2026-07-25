import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import Layout from "../components/Layout";
import { API_BASE } from "../lib/runtime";

interface LandlordDetail {
  landlord: Record<string, unknown>;
  has_password: boolean;
  has_totp: boolean;
  stats: {
    tenants: number;
    receipts: number;
    kyc: number;
    pending_revenue: number;
  };
}

interface CreatorInfo {
  landlord_id: number;
  username: string;
  full_name: string;
  self_registered: boolean;
  created_at: string;
  signup_details: {
    ip_address: string | null;
    timestamp: string | null;
    user_agent: string | null;
  };
  last_login: {
    timestamp: string | null;
    ip_address: string | null;
  };
}

function StatBox({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <div style={{
      background: "#f9fafb", borderRadius: 10, padding: "16px 20px", flex: "1 1 140px", minWidth: 130,
      borderLeft: `4px solid ${color}`,
    }}>
      <div style={{ fontSize: 24, fontWeight: 700, color: "#1a1d2e" }}>{value}</div>
      <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>{label}</div>
    </div>
  );
}

export default function LandlordDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<LandlordDetail | null>(null);
  const [creator, setCreator] = useState<CreatorInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      fetch(`${API_BASE}/landlords/${id}/details`, { credentials: "include" }).then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      }),
      fetch(`${API_BASE}/landlords/${id}/creator-info`, { credentials: "include" }).then((r) => r.ok ? r.json() : null),
    ])
      .then(([d, c]) => { setDetail(d); setCreator(c); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Layout><p style={{ color: "#9ca3af" }}>Loading…</p></Layout>;
  if (error) return <Layout><p style={{ color: "#dc2626" }}>{error}</p></Layout>;
  if (!detail) return <Layout><p style={{ color: "#9ca3af" }}>Landlord not found.</p></Layout>;

  const l = detail.landlord;
  const statusColor = l.status === "Active" ? "#22c55e" : l.status === "Locked" ? "#ef4444" : "#6b7280";

  return (
    <Layout>
      <Link to="/landlords" style={{ fontSize: 13, color: "#3b4a6b", textDecoration: "none", marginBottom: 16, display: "inline-block" }}>
        ← Back to Landlords
      </Link>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: "#1a1d2e" }}>
            {String(l.full_name || l.username)}
          </h1>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "#6b7280" }}>
            @{String(l.username)} · {String(l.email || "no email")}
          </p>
        </div>
        <span style={{
          display: "inline-block", padding: "4px 14px", borderRadius: 99, fontSize: 13, fontWeight: 600,
          background: `${statusColor}20`, color: statusColor,
        }}>
          {String(l.status)}
        </span>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 16, marginBottom: 28 }}>
        <StatBox label="Tenants" value={detail.stats.tenants} color="#3b82f6" />
        <StatBox label="Receipts" value={detail.stats.receipts} color="#22c55e" />
        <StatBox label="KYC Files" value={detail.stats.kyc} color="#a855f7" />
        <StatBox label="Pending Revenue" value={`₱${detail.stats.pending_revenue.toLocaleString()}`} color="#f59e0b" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div style={{ background: "#fff", borderRadius: 14, padding: "24px 28px", boxShadow: "0 2px 12px rgba(0,0,0,0.07)" }}>
          <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 600, color: "#374151" }}>Account Details</h2>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
            <tbody>
              {[
                ["Landlord ID", l.id],
                ["UUID", l.landlord_uuid],
                ["Phone", l.phone],
                ["Created", l.created_at ? new Date(String(l.created_at)).toLocaleString() : "—"],
                ["Updated", l.updated_at ? new Date(String(l.updated_at)).toLocaleString() : "—"],
                ["Has Password", detail.has_password ? "Yes" : "No"],
                ["Has TOTP", detail.has_totp ? "Yes" : "No"],
                ["Failed Attempts", l.failed_attempts ?? 0],
                ["Locked Until", l.locked_until ? new Date(String(l.locked_until)).toLocaleString() : "—"],
                ["PW Change Required", l.requires_password_change ? "Yes (forced)" : "No"],
              ].map(([label, value]) => (
                <tr key={String(label)} style={{ borderBottom: "1px solid #f3f4f6" }}>
                  <td style={{ padding: "10px 0", fontWeight: 600, color: "#6b7280", width: 140 }}>{String(label)}</td>
                  <td style={{ padding: "10px 0", color: "#1a1d2e" }}>{String(value ?? "—")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {creator && (
          <div style={{ background: "#fff", borderRadius: 14, padding: "24px 28px", boxShadow: "0 2px 12px rgba(0,0,0,0.07)" }}>
            <h2 style={{ margin: "0 0 16px", fontSize: 16, fontWeight: 600, color: "#374151" }}>Creator Info</h2>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <tbody>
                {[
                  ["Registered By", creator.self_registered ? "Self-registered" : "Platform Admin"],
                  ["Signup IP", creator.signup_details.ip_address ?? "—"],
                  ["Signup Time", creator.signup_details.timestamp ? new Date(creator.signup_details.timestamp).toLocaleString() : "—"],
                  ["Last Login", creator.last_login.timestamp ? new Date(creator.last_login.timestamp).toLocaleString() : "Never"],
                  ["Last Login IP", creator.last_login.ip_address ?? "—"],
                ].map(([label, value]) => (
                  <tr key={String(label)} style={{ borderBottom: "1px solid #f3f4f6" }}>
                    <td style={{ padding: "10px 0", fontWeight: 600, color: "#6b7280", width: 140 }}>{String(label)}</td>
                    <td style={{ padding: "10px 0", color: "#1a1d2e" }}>{String(value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  );
}
