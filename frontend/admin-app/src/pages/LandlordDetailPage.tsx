import { useEffect, useState } from "react";
import { useParams, Link } from "react-router";
import Layout from "../components/Layout";
import { fetchApi } from "../api/client";
import { Card } from "../components/ui/card";

interface LandlordDetail {
  landlord: Record<string, unknown>;
  has_password: boolean;
  has_totp: boolean;
  stats: {
    tenants: number;
    receipts: number;
    kyc: number;
    pending_revenue: number;
  };
}

interface CreatorInfo {
  landlord_id: number;
  username: string;
  full_name: string;
  self_registered: boolean;
  created_at: string;
  signup_details: {
    ip_address: string | null;
    timestamp: string | null;
    user_agent: string | null;
  };
  last_login: {
    timestamp: string | null;
    ip_address: string | null;
  };
}

function StatBox({ label, value, colorClass }: { label: string; value: number | string; colorClass: string }) {
  return (
    <div className={`min-w-[130px] flex-[1_1_140px] rounded-[10px] bg-[#f9fafb] p-5 ${colorClass}`}>
      <div className="text-2xl font-bold text-[#1a1d2e]">{value}</div>
      <div className="mt-1 text-xs text-gray-400">{label}</div>
    </div>
  );
}

function InfoList({ rows, className }: { rows: unknown[][]; className?: string }) {
  return (
    <div className={`text-sm ${className ?? ""}`}>
      {rows.map(([label, value]) => (
        <div key={String(label)} className="flex gap-4 border-b border-gray-100 py-2.5 last:border-0">
          <span className="w-[150px] shrink-0 font-semibold text-gray-500">{String(label)}</span>
          <span className="break-all text-[#1a1d2e]">{String(value ?? "—")}</span>
        </div>
      ))}
    </div>
  );
}

export default function LandlordDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<LandlordDetail | null>(null);
  const [creator, setCreator] = useState<CreatorInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      fetchApi(`/landlords/${id}/details`).then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      }),
      fetchApi(`/landlords/${id}/creator-info`).then((r) => r.ok ? r.json() : null),
    ])
      .then(([d, c]) => { setDetail(d); setCreator(c); })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <Layout><p className="text-gray-400">Loading…</p></Layout>;
  if (error) return <Layout><p className="text-red-600">{error}</p></Layout>;
  if (!detail) return <Layout><p className="text-gray-400">Landlord not found.</p></Layout>;

  const l = detail.landlord;
  const statusTone =
    l.status === "Active"
      ? "bg-green-500/15 text-green-600"
      : l.status === "Locked"
        ? "bg-red-500/15 text-red-600"
        : "bg-gray-500/15 text-gray-600";

  return (
    <Layout>
      <Link to="/landlords" className="mb-4 inline-block text-[13px] text-[#3b4a6b] no-underline hover:underline">
        ← Back to Landlords
      </Link>

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="m-0 text-2xl font-bold text-[#1a1d2e]">
            {String(l.full_name || l.username)}
          </h1>
          <p className="mt-1 text-[13px] text-gray-500">
            @{String(l.username)} · {String(l.email || "no email")}
          </p>
        </div>
        <span className={`inline-block whitespace-nowrap rounded-full px-3.5 py-1 text-[13px] font-semibold ${statusTone}`}>
          {String(l.status)}
        </span>
      </div>

      <div className="mb-7 flex flex-wrap gap-4">
        <StatBox label="Tenants" value={detail.stats.tenants} colorClass="border-l-4 border-l-blue-500" />
        <StatBox label="Receipts" value={detail.stats.receipts} colorClass="border-l-4 border-l-green-500" />
        <StatBox label="KYC Files" value={detail.stats.kyc} colorClass="border-l-4 border-l-purple-500" />
        <StatBox label="Pending Revenue" value={`₱${detail.stats.pending_revenue.toLocaleString()}`} colorClass="border-l-4 border-l-amber-500" />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card className="rounded-2xl p-7 shadow-[0_2px_12px_rgba(0,0,0,0.07)]">
          <h2 className="mb-4 text-base font-semibold text-gray-700">Account Details</h2>
          <InfoList
            rows={[
              ["Landlord ID", l.id],
              ["UUID", l.landlord_uuid],
              ["Phone", l.phone],
              ["Created", l.created_at ? new Date(String(l.created_at)).toLocaleString() : null],
              ["Updated", l.updated_at ? new Date(String(l.updated_at)).toLocaleString() : null],
              ["Has Password", detail.has_password ? "Yes" : "No"],
              ["Has TOTP", detail.has_totp ? "Yes" : "No"],
              ["Failed Attempts", l.failed_attempts ?? 0],
              ["Locked Until", l.locked_until ? new Date(String(l.locked_until)).toLocaleString() : null],
              ["PW Change Required", l.requires_password_change ? "Yes (forced)" : "No"],
              ["Privacy Accepted", l.privacy_consented ? "Yes" : "Pending"],
              ["Privacy Version", l.privacy_version ?? null],
              ["Privacy Accepted At", l.privacy_accepted_at ? new Date(String(l.privacy_accepted_at)).toLocaleString() : null],
              ["Privacy Accepted IP", l.privacy_accepted_ip ?? null],
              ["Terms Accepted", l.terms_consented ? "Yes" : "Pending"],
              ["Terms Version", l.terms_version ?? null],
              ["Terms Accepted At", l.terms_accepted_at ? new Date(String(l.terms_accepted_at)).toLocaleString() : null],
              ["Terms Accepted IP", l.terms_accepted_ip ?? null],
            ]}
          />
        </Card>

        {creator && (
          <Card className="rounded-2xl p-7 shadow-[0_2px_12px_rgba(0,0,0,0.07)]">
            <h2 className="mb-4 text-base font-semibold text-gray-700">Creator Info</h2>
            <InfoList
              rows={[
                ["Registered By", creator.self_registered ? "Self-registered" : "Platform Admin"],
                ["Signup IP", creator.signup_details.ip_address ?? null],
                ["Signup Time", creator.signup_details.timestamp ? new Date(creator.signup_details.timestamp).toLocaleString() : null],
                ["Last Login", creator.last_login.timestamp ? new Date(creator.last_login.timestamp).toLocaleString() : "Never"],
                ["Last Login IP", creator.last_login.ip_address ?? null],
              ]}
            />
          </Card>
        )}
      </div>
    </Layout>
  );
}