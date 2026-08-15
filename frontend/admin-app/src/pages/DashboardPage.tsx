import { useEffect, useState } from "react";
import { Link } from "react-router";
import Layout from "../components/Layout";
import { API_BASE } from "../lib/runtime";

interface Stats {
  total_landlords: number;
  active_landlords: number;
  total_admins: number;
  total_tenants: number;
}

function StatCard({ icon, label, value, color }: { icon: string; label: string; value: number | string; color: string }) {
  return (
    <div style={{
      background: "#fff", borderRadius: 14, padding: "24px 28px",
      boxShadow: "0 2px 12px rgba(0,0,0,0.07)", flex: "1 1 200px", minWidth: 180,
      borderTop: `4px solid ${color}`,
    }}>
      <div style={{ fontSize: 28, marginBottom: 10 }}>{icon}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: "#1a1d2e" }}>{value}</div>
      <div style={{ fontSize: 13, color: "#6b7280", marginTop: 4 }}>{label}</div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    fetch(`${API_BASE}/stats`, { credentials: "include" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setStats)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    fetch(`${API_BASE}/feedback/unread-count`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setUnread(data?.unread ?? 0))
      .catch(() => {});
  }, []);

  return (
    <Layout>
      <h1 style={{ margin: "0 0 24px", fontSize: 26, fontWeight: 700, color: "#1a1d2e" }}>
        Dashboard
      </h1>

      {unread > 0 && (
        <Link to="/feedback" style={{ textDecoration: "none", display: "block", marginBottom: 20 }}>
          <div style={{
            background: "#fffbeb", border: "1px solid #fde68a", borderRadius: 10,
            padding: "14px 18px", display: "flex", alignItems: "center", gap: 12,
            cursor: "pointer",
          }}>
            <span style={{ fontSize: 22 }}>📬</span>
            <div style={{ flex: 1 }}>
              <strong style={{ color: "#92400e", fontSize: 14 }}>
                {unread} pending QR feedback {unread === 1 ? "item" : "items"}
              </strong>
              <p style={{ margin: "2px 0 0", fontSize: 13, color: "#b45309" }}>
                Tenants reported a wrong QR key on the unlock screen. Review and provide a fix.
              </p>
            </div>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#92400e" }}>View inbox →</span>
          </div>
        </Link>
      )}

      {error && (
        <div style={{ background: "#fef2f2", color: "#dc2626", padding: "12px 16px", borderRadius: 8, marginBottom: 20, fontSize: 14 }}>
          Error loading stats: {error}
        </div>
      )}

      {!stats && !error && (
        <p style={{ color: "#9ca3af" }}>Loading stats…</p>
      )}

      {stats && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 20, marginBottom: 32 }}>
          <StatCard icon="🏢" label="Total Landlords"  value={stats.total_landlords}  color="#3b82f6" />
          <StatCard icon="✅" label="Active Landlords" value={stats.active_landlords} color="#22c55e" />
          <StatCard icon="👤" label="Admin Accounts"  value={stats.total_admins}     color="#a855f7" />
          <StatCard icon="🏠" label="Total Tenants"   value={stats.total_tenants}    color="#f59e0b" />
        </div>
      )}

      <div style={{ background: "#fff", borderRadius: 14, padding: "24px 28px", boxShadow: "0 2px 12px rgba(0,0,0,0.07)" }}>
        <h2 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 600, color: "#374151" }}>Quick Actions</h2>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Link to="/landlords"
            style={{ padding: "10px 20px", borderRadius: 8, background: "#3b4a6b", color: "#fff", textDecoration: "none", fontSize: 14, fontWeight: 600 }}>
            Manage Landlords
          </Link>
        </div>
      </div>
    </Layout>
  );
}
