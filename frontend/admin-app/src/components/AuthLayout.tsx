import type { ReactNode } from "react";
import { Globe } from "lucide-react";
import { Logo } from "@shared/brand/Logo";

const NAV_LINKS = [
  { label: "Home", href: "/", Icon: Globe },
  // { label: "Landlord Portal", href: "/landlord/login", icon: "🏠" },
  // { label: "Tenant Portal", href: "/tenant", icon: "👤" },
];

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-[#1a1d2e] via-[#2d3561] to-[#1a1d2e] font-sans">
      {/* Header */}
      <header className="flex flex-wrap items-center justify-between gap-3 px-8 py-4">
        <a href="/admin/login" className="flex items-center gap-2.5 no-underline">
          <Logo variant="light" height={22} />
        </a>
        <nav className="flex gap-2.5">
          {NAV_LINKS.map(({ label, href, Icon }) => (
            <a
              key={href}
              href={href}
              className="flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-[13px] font-semibold text-white/75 no-underline transition-colors hover:bg-white/20 hover:text-white"
            >
              <Icon size={14} />
              {label}
            </a>
          ))}
        </nav>
      </header>

      {/* Content */}
      <div className="flex flex-1 items-center justify-center px-4">
        {children}
      </div>

      {/* Footer */}
      <footer className="border-t border-white/10 px-8 py-4 text-center">
        <p className="m-0 text-xs text-white/45">
          &copy; {new Date().getFullYear()} <Logo variant="light" height={10} /> by Vijay Kumar Sharma. All rights reserved.
        </p>
      </footer>
    </div>
  );
}