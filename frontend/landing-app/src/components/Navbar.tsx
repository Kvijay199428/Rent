import { useState } from "react";
import { navLinks } from "../data";
import { ArrowUpRightIcon, HomeIcon, ShieldIcon, UserIcon } from "./Icons";

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  const logins = [
    { label: "Landlord", href: "/rent/landlord/login", icon: HomeIcon },
    { label: "Tenant", href: "/rent/tenant/login", icon: UserIcon },
    { label: "Admin", href: "/rent/admin/login", icon: ShieldIcon },
  ];

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <a href="#" className="navbar-logo" aria-label="Home">
          <span className="logo-icon" style={{ width: 38, height: 38, fontSize: 15 }}>PA</span>
          <span className="logo-text">
            <span>PROP</span><span style={{ color: "var(--accent)" }}>AURA</span>
          </span>
        </a>

        <ul className={`navbar-links ${mobileOpen ? "open" : ""}`}>
          {navLinks.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </a>
            </li>
          ))}
          {logins.map((login) => {
            const IconCmp = login.icon;
            return (
              <li key={login.label} className="navbar-mobile-login">
                <a
                  href={login.href}
                  onClick={() => setMobileOpen(false)}
                  style={{ display: "flex", alignItems: "center", gap: 8 }}
                >
                  <IconCmp size={18} />
                  {login.label} Login
                </a>
              </li>
            );
          })}
        </ul>

        <div className="navbar-logins">
          <a href="/rent/landlord/login" className="btn btn-ghost btn-sm">
            <HomeIcon size={14} /> Landlord
          </a>
          <a href="/rent/tenant/login" className="btn btn-ghost btn-sm">
            <UserIcon size={14} /> Tenant
          </a>
          <a href="/rent/admin/login" className="btn btn-primary btn-sm">
            Admin <ArrowUpRightIcon size={14} />
          </a>
        </div>

        <button
          className="navbar-toggle"
          aria-label="Toggle menu"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          <span className={`hamburger ${mobileOpen ? "open" : ""}`} />
        </button>
      </div>
    </nav>
  );
}
