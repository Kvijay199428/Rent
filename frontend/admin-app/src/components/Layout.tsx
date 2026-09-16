import { Link, useLocation, useNavigate } from "react-router";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Building2,
  Inbox,
  Search,
  ClipboardList,
  Settings,
  Globe,
  User,
  LogOut,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { fetchApi } from "../api/client";
import { Logo } from "@shared/brand/Logo";

const NAV = [
  { to: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { to: "/landlords", label: "Landlords", Icon: Building2 },
  { to: "/feedback", label: "Feedback", Icon: Inbox },
  { to: "/explorer", label: "Data Explorer", Icon: Search },
  { to: "/audit-logs", label: "Audit Logs", Icon: ClipboardList },
  { to: "/settings", label: "Settings", Icon: Settings },
];

const QUICK_LINKS = [
  { href: "/", label: "Home", Icon: Globe },
  { href: "/landlord/login", label: "Landlord Portal", Icon: Building2 },
  { href: "/tenant", label: "Tenant Portal", Icon: User },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { admin, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    fetchApi("/feedback/unread-count")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setUnread(data?.unread ?? 0))
      .catch(() => {});
  }, [location.pathname]);

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen bg-slate-100 font-sans">
      <aside className="fixed inset-y-0 left-0 z-[100] flex w-[220px] flex-col bg-[#1a1d2e] py-6 text-slate-300">
        <div className="border-b border-white/10 px-5 pb-6">
          <p className="mb-1"><Logo variant="light" height={20} /></p>
          <p className="m-0 text-sm font-semibold text-[#e9ecf2]">Control Panel</p>
        </div>
        <nav className="flex-1 px-3 py-4">
          {NAV.map(({ to, label, Icon }) => {
            const active = to === "/landlords"
              ? location.pathname.startsWith("/landlords")
              : location.pathname.startsWith(to);
            const showBadge = to === "/feedback" && unread > 0;
            return (
              <Link
                key={to}
                to={to}
                aria-current={active ? "page" : undefined}
                className={`mb-1 flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm no-underline transition-colors ${
                  active
                    ? "bg-[#3b4a6b] font-semibold text-white"
                    : "text-slate-400 hover:bg-white/5"
                }`}
              >
                <Icon size={16} />
                <span className="flex-1">{label}</span>
                {showBadge && (
                  <span className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-red-500 px-[5px] text-[11px] font-bold text-white">
                    {unread > 99 ? "99+" : unread}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/10 px-3 py-4">
          <p className="mb-2 px-3 text-[11px] font-bold uppercase tracking-wide text-slate-500">
            Quick Access
          </p>
          <div className="mb-3 flex flex-col gap-1 px-1">
            {QUICK_LINKS.map(({ href, label, Icon }) => (
              <a
                key={href}
                href={href}
                className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-[13px] font-medium text-slate-400 no-underline hover:bg-white/10"
              >
                <Icon size={14} />
                {label}
              </a>
            ))}
          </div>

          <div className="border-t border-white/10 pt-3">
            <p className="mb-2 px-3 text-[13px] text-slate-400">
              Logged in as <strong className="text-[#e9ecf2]">{admin?.username ?? "…"}</strong>
            </p>
            <button
              onClick={handleLogout}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-red-500 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-red-600"
            >
              <LogOut size={14} />
              Log out
            </button>
          </div>
          <p className="mt-2.5 text-center text-[10px] text-slate-600">
            &copy; {new Date().getFullYear()} <Logo variant="light" height={10} /> by Vijay Kumar Sharma. All rights reserved.
          </p>
        </div>
      </aside>

      <main className="ml-[220px] flex-1 p-8">
        {children}
      </main>
    </div>
  );
}