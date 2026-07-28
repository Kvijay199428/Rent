import { Link, useLocation } from 'react-router-dom';
import { useState } from 'react';
import {
  LayoutDashboard,
  Receipt,
  Clock,
  Users,
  Archive,
  Database,
  Settings,
  Menu,
  X,
  ReceiptIcon,
  Shield,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const menuItems = [
  { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
  { name: 'Billing', icon: Receipt, path: '/billing' },
  { name: 'History', icon: Clock, path: '/history' },
  { name: 'Tenants', icon: Users, path: '/tenants' },
  { name: 'Archive', icon: Archive, path: '/archive' },
  { name: 'Activity', icon: Shield, path: '/activity' },
  { name: 'Backups', icon: Database, path: '/backups' },
  { name: 'Settings', icon: Settings, path: '/settings' },
];

export default function Sidebar() {
  const location = useLocation();
  const { logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setMobileOpen(!mobileOpen)}
        className="lg:hidden fixed top-3 left-3 z-50 p-2 rounded-lg bg-background border shadow-sm"
        aria-label="Toggle menu"
      >
        {mobileOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:sticky top-0 left-0 z-40 h-screen w-64 bg-card border-r flex flex-col transition-transform duration-200 lg:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center gap-2 px-4 h-14 border-b">
          <ReceiptIcon className="h-5 w-5 text-primary" />
          <span className="font-bold text-xl"><span style={{color:"#708498"}}>PROP</span><span style={{color:"#95A58F"}}>AURA</span></span>
          <button
            onClick={() => setMobileOpen(false)}
            className="lg:hidden ml-auto p-1 rounded hover:bg-accent"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-3">
          <ul className="space-y-1">
            {menuItems.map((item) => {
              const active = isActive(item.path);
              return (
                <li key={item.path}>
                  <Link
                    to={item.path}
                    onClick={() => setMobileOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      active
                        ? 'bg-primary text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                    }`}
                  >
                    <item.icon size={18} />
                    {item.name}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="border-t p-3">
          {/* Cross-app quick access */}
          <p className="px-2 mb-2 text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
            Quick Access
          </p>
          <div className="flex flex-col gap-1 mb-3 px-1">
            <a href="/rent/" className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border/50 bg-muted/50 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors no-underline">
              <span className="text-base">🌍</span>
              Home
            </a>
            <a href="/rent/platform-admin/login" className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border/50 bg-muted/50 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors no-underline">
              <span className="text-base">⚙️</span>
              Platform Admin
            </a>
            <a href="/rent/tenant" className="flex items-center gap-2 px-3 py-2 rounded-lg border border-border/50 bg-muted/50 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors no-underline">
              <span className="text-base">👤</span>
              Tenant Portal
            </a>
          </div>

          <div className="border-t pt-3">
            <div className="flex items-center gap-2 mb-2 px-2">
              <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-bold">
                A
              </div>
              <span className="text-sm text-muted-foreground font-medium">Landlord User</span>
            </div>
            <button
              onClick={logout}
              className="w-full text-left px-3 py-2 text-sm text-muted-foreground hover:bg-accent rounded-lg transition-colors"
            >
              Logout
            </button>
            <p className="text-center mt-2 text-[10px] text-muted-foreground">
              &copy; {new Date().getFullYear()} PROPAURA by Vijay Kumar Sharma. All rights reserved.
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
