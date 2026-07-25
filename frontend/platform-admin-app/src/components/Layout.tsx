import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: "📊" },
  { to: "/landlords", label: "Landlords", icon: "🏠" },
  { to: "/explorer", label: "Data Explorer", icon: "🔍" },
  { to: "/settings",  label: "Settings",  icon: "⚙️"  },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { admin, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "system-ui, sans-serif", background: "#f4f6fa" }}>
      <aside style={{
        width: 220,
        background: "#1a1d2e",
        color: "#c9cdd8",
        display: "flex",
        flexDirection: "column",
        padding: "24px 0",
        position: "fixed",
        inset: "0 auto 0 0",
        zIndex: 100,
      }}>
        <div style={{ padding: "0 20px 24px", borderBottom: "1px solid #2c2f3f" }}>
          <p style={{ fontSize: 11, color: "#6b7280", marginBottom: 4, textTransform: "uppercase", letterSpacing: 1 }}><span style={{color:"#708498"}}>PROP</span><span style={{color:"#95A58F"}}>AURA</span></p>
          <p style={{ fontSize: 14, fontWeight: 600, color: "#e9ecf2", margin: 0 }}>Control Panel</p>
        </div>
        <nav style={{ flex: 1, padding: "16px 12px" }}>
          {NAV.map(({ to, label, icon }) => {
            const active = to === "/landlords"
              ? location.pathname.startsWith("/landlords")
              : location.pathname.startsWith(to);
            return (
              <Link
                key={to}
                to={to}
                style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "10px 12px", borderRadius: 8, marginBottom: 4,
                  color: active ? "#fff" : "#9ca3af",
                  background: active ? "#3b4a6b" : "transparent",
                  textDecoration: "none", fontSize: 14, fontWeight: active ? 600 : 400,
                  transition: "background 0.15s",
                }}
              >
                <span>{icon}</span>
                {label}
              </Link>
            );
          })}
        </nav>
        <div style={{ padding: "16px 20px", borderTop: "1px solid #2c2f3f" }}>
          <p style={{ margin: "0 0 8px", fontSize: 13, color: "#9ca3af" }}>
            Logged in as <strong style={{ color: "#e9ecf2" }}>{admin?.username ?? "…"}</strong>
          </p>
          <button
            onClick={handleLogout}
            style={{
              width: "100%", padding: "8px 0", borderRadius: 6, border: "none",
              background: "#ef4444", color: "#fff", fontSize: 13, cursor: "pointer", fontWeight: 600,
            }}
          >
            Log out
          </button>
        </div>
      </aside>

      <main style={{ marginLeft: 220, flex: 1, padding: 32 }}>
        {children}
      </main>
    </div>
  );
}
