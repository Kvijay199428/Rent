import { useState } from "react";
import { navLinks } from "../data";
import { ArrowUpRightIcon, HomeIcon, UserIcon } from "./Icons";
import { Logo } from "@shared/brand/Logo";

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="navbar motion-slide-in-top">
      <div className="navbar-inner">
        <a href="#" className="navbar-logo" aria-label="Home">
          <Logo height={22} />
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
        </ul>

        <div className="navbar-logins">
          <a href="/landlord/login" className="btn btn-ghost btn-sm">
            <HomeIcon size={14} /> Landlord
          </a>
          <a href="/tenant/login" className="btn btn-ghost btn-sm">
            <UserIcon size={14} /> Tenant
          </a>
          <a href="/admin/login" className="btn btn-primary btn-sm">
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
