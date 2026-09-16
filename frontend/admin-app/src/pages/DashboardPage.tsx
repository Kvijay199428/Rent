import { useEffect, useState } from "react";
import { Link } from "react-router";
import Layout from "../components/Layout";
import { fetchApi } from "../api/client";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";

interface Stats {
  total_landlords: number;
  active_landlords: number;
  total_admins: number;
  total_tenants: number;
}

function StatCard({ icon, label, value, colorClass }: { icon: string; label: string; value: number | string; colorClass: string }) {
  return (
    <Card className={`min-w-[180px] flex-1 basis-[200px] rounded-2xl border-t-4 ${colorClass}`}>
      <CardContent className="p-6">
        <div className="mb-2.5 text-[28px]">{icon}</div>
        <div className="text-[28px] font-bold text-[#1a1d2e]">{value}</div>
        <div className="mt-1 text-[13px] text-gray-500">{label}</div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    fetchApi("/stats")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setStats)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    fetchApi("/feedback/unread-count")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setUnread(data?.unread ?? 0))
      .catch(() => {});
  }, []);

  return (
    <Layout>
      <h1 className="mb-6 text-[26px] font-bold text-[#1a1d2e]">
        Dashboard
      </h1>

      {unread > 0 && (
        <Link to="/feedback" className="mb-5 block no-underline">
          <div className="flex cursor-pointer items-center gap-3 rounded-[10px] border border-amber-200 bg-amber-50 p-3.5">
            <span className="text-[22px]">📬</span>
            <div className="flex-1">
              <strong className="text-sm text-amber-800">
                {unread} pending QR feedback {unread === 1 ? "item" : "items"}
              </strong>
              <p className="mt-0.5 text-[13px] text-amber-700">
                Tenants reported a wrong QR key on the unlock screen. Review and provide a fix.
              </p>
            </div>
            <span className="text-[13px] font-bold text-amber-800">View inbox →</span>
          </div>
        </Link>
      )}

      {error && (
        <div className="mb-5 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
          Error loading stats: {error}
        </div>
      )}

      {!stats && !error && (
        <p className="text-gray-400">Loading stats…</p>
      )}

      {stats && (
        <div className="motion-stagger mb-8 flex flex-wrap gap-5">
          <StatCard icon="🏢" label="Total Landlords"  value={stats.total_landlords}  colorClass="border-t-blue-500" />
          <StatCard icon="✅" label="Active Landlords" value={stats.active_landlords} colorClass="border-t-green-500" />
          <StatCard icon="👤" label="Admin Accounts"  value={stats.total_admins}     colorClass="border-t-purple-500" />
          <StatCard icon="🏠" label="Total Tenants"   value={stats.total_tenants}    colorClass="border-t-amber-500" />
        </div>
      )}

      <Card className="motion-fade-up rounded-2xl shadow-[0_2px_12px_rgba(0,0,0,0.07)]">
        <CardContent className="p-6">
          <h2 className="mb-3 text-base font-semibold text-gray-700">Quick Actions</h2>
          <div className="flex flex-wrap gap-3">
            <Button asChild className="bg-[#3b4a6b] text-sm font-semibold text-white hover:bg-[#34405a]">
              <Link to="/landlords">Manage Landlords</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </Layout>
  );
}