import type { ReactNode } from "react";

const NAV_LINKS = [
  { label: "Home", href: "/rent/", icon: "🌍" },
  // { label: "Landlord Portal", href: "/rent/landlord/login", icon: "🏠" },
  // { label: "Tenant Portal", href: "/rent/tenant", icon: "👤" },
];

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      background: "linear-gradient(135deg, #1a1d2e 0%, #2d3561 100%)",
      fontFamily: "system-ui, sans-serif",
    }}>
      {/* Header */}
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "16px 32px", flexWrap: "wrap", gap: 12,
      }}>
        <a href="/rent/admin/login" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
          <span style={{
            width: 36, height: 36, borderRadius: 10, display: "flex",
            alignItems: "center", justifyContent: "center",
            background: "rgba(255,255,255,0.15)", color: "#fff",
            fontSize: 18, fontWeight: 700,
          }}>P</span>
          <span style={{ fontSize: 18, fontWeight: 700 }}>
            <span style={{ color: "#a0b4c8" }}>PROP</span>
            <span style={{ color: "#95A58F" }}>AURA</span>
          </span>
        </a>
        <nav style={{ display: "flex", gap: 10 }}>
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "8px 16px", borderRadius: 9999,
                border: "1px solid rgba(255,255,255,0.18)",
                background: "rgba(255,255,255,0.08)",
                color: "rgba(255,255,255,0.75)",
                fontSize: 13, fontWeight: 600, textDecoration: "none",
                transition: "background 0.15s, color 0.15s",
              }}
            >
              <span style={{ fontSize: 14 }}>{link.icon}</span>
              {link.label}
            </a>
          ))}
        </nav>
      </header>

      {/* Content */}
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "0 16px" }}>
        {children}
      </div>

      {/* Footer */}
      <footer style={{ borderTop: "1px solid rgba(255,255,255,0.08)", padding: "16px 32px", textAlign: "center" }}>
        <p style={{ margin: 0, fontSize: 12, color: "rgba(255,255,255,0.45)" }}>
          &copy; {new Date().getFullYear()} PROPAURA by Vijay Kumar Sharma. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
