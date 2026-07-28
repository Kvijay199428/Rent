import type { ReactNode } from "react";

const NAV_LINKS = [
  { label: "Home", href: "/rent/", icon: "🌍" },
  { label: "Platform Admin", href: "/rent/platform-admin/login", icon: "⚙️" },
  { label: "Landlord Portal", href: "/rent/landlord/login", icon: "🏠" },
];

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-muted/30">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 flex-wrap gap-3">
        <a href="/rent/platform-admin/login" className="flex items-center gap-2.5 no-underline">
          <span className="flex items-center justify-center w-9 h-9 rounded-[10px] bg-slate-900/10 dark:bg-white/10 text-slate-900 dark:text-white text-base font-bold">
            P
          </span>
          <span className="text-lg font-bold">
            <span className="text-slate-500 dark:text-slate-400">PROP</span>
            <span className="text-[#95A58F]">AURA</span>
          </span>
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
          &copy; {new Date().getFullYear()} PROPAURA by Vijay Kumar Sharma. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
