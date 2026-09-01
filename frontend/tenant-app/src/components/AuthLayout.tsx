import type { ReactNode } from "react";
import { Logo } from "@shared/brand/Logo";

const NAV_LINKS = [
  { label: "Home", href: "/rent/", icon: "🌍" },
  // { label: "Platform Admin", href: "/rent/admin/login", icon: "⚙️" },
  // { label: "Landlord Portal", href: "/rent/landlord/login", icon: "🏠" },
];

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-muted/30">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 flex-wrap gap-3">
        <a href="/rent/admin/login" className="flex items-center gap-2.5 no-underline">
          <Logo height={22} />
        </a>
        <nav className="flex gap-2.5">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full border border-slate-200 dark:border-white/15 bg-white/60 dark:bg-white/8 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-white/15 hover:text-slate-900 dark:hover:text-white transition-colors no-underline"
            >
              <span className="text-base">{link.icon}</span>
              {link.label}
            </a>
          ))}
        </nav>
      </header>

      {/* Content */}
      <main className="flex-1 flex items-center justify-center px-4 pb-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-white/10 py-4 text-center">
        <p className="text-xs text-muted-foreground m-0">
          &copy; {new Date().getFullYear()} <Logo height={10} /> by Vijay Kumar Sharma. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
