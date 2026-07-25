import { useState } from "react";
import { navLinks } from "../data";

export default function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <a href="#" className="navbar-logo" aria-label="Home">
          <span className="logo-icon" style={{width: 36, height: 36, fontSize: 18}}>P</span>
          <span className="logo-text"><span style={{color:"#708498"}}>PROP</span><span style={{color:"#95A58F"}}>AURA</span></span>
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

        <a href="#cta" className="navbar-cta">
          Get Early Access
        </a>

        <button
          className="navbar-toggle"
          aria-label="Toggle menu"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          <span className={`hamburger ${mobileOpen ? "open" : ""}`} />
        </button>
      </div>
    </nav>
  );
}
