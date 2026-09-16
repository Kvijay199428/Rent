import { useEffect, useState } from "react";
import { toast } from "sonner";
import Layout from "../components/Layout";
import { fetchApi } from "../api/client";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";

interface FeedbackItem {
  id: number;
  username: string;
  display_name: string;
  email: string;
  message: string;
  qr_key: string | null;
  status: "open" | "resolved";
  admin_reply: string | null;
  created_at: string;
  diagnostics?: Record<string, string>[];
}

function formatTs(ts: string): string {
  const d = new Date(ts);
  const date = d.toISOString().slice(0, 10);
  const time = d.toISOString().slice(11, 16);
  return `${date} ${time} (UTC)`;
}

function StatusBadge({ status }: { status: FeedbackItem["status"] }) {
  const open = status !== "resolved";
  return (
    <Badge
      className={`rounded-full border-transparent px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide ${
        open ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"
      }`}
    >
      {open ? "Open" : "Resolved"}
    </Badge>
  );
}

function Diagnostics({ diag, className }: { diag: Record<string, string>[]; className?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={className}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="cursor-pointer text-[12px] font-semibold text-[#3b4a6b]"
      >
        {open ? "▾" : "▸"} Diagnostics
      </button>
      {open && (
        <div className="mt-2 overflow-x-auto rounded-lg border border-gray-200 bg-slate-50 p-3">
          <table className="w-full text-[12px]">
            <tbody>
              {diag.map((row, i) =>
                Object.entries(row).map(([k, v]) => (
                  <tr key={`${k}-${i}`} className="border-b border-gray-100 last:border-0">
                    <td className="whitespace-nowrap py-1.5 pr-4 font-semibold text-gray-500">{k}</td>
                    <td className="break-all py-1.5 text-[#1a1d2e]">{v}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function FeedbackInboxPage() {
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [total, setTotal] = useState(0);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [offset, setOffset] = useState(0);
  const [limit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [replyText, setReplyText] = useState<Record<number, string>>({});

  const params = () => {
    const p = new URLSearchParams();
    if (search) p.set("search", search);
    if (statusFilter && statusFilter !== "all") p.set("status", statusFilter);
    p.set("limit", String(limit));
    p.set("offset", String(offset));
    return p;
  };

  const fetchFeedback = async () => {
    setLoading(true);
    try {
      const res = await fetchApi(`/feedback?${params()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
      setCounts(data.counts || {});
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load feedback");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchFeedback(); }, [offset, limit, statusFilter, search]);

  const resetFilters = () => {
    setSearch("");
    setStatusFilter("all");
    setOffset(0);
  };

  const hasFilters = search || statusFilter !== "all";

  const setReply = (id: number, val: string) => setReplyText((prev) => ({ ...prev, [id]: val }));

  const handleReply = async (id: number) => {
    const text = (replyText[id] || "").trim();
    if (!text) { toast.error("Please write a reply first"); return; }
    setBusyId(id);
    try {
      const res = await fetchApi(`/feedback/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ admin_reply: text, status: "resolved" }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      toast.success("Reply sent & marked as resolved");
      setReply(id, "");
      await fetchFeedback();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to send reply");
    } finally {
      setBusyId(null);
    }
  };

  const handleResolve = async (id: number) => {
    setBusyId(id);
    try {
      const res = await fetchApi(`/feedback/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "resolved" }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      toast.success("Marked as resolved");
      await fetchFeedback();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to update status");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <Layout>
      <h1 className="mb-6 text-[26px] font-bold text-[#1a1d2e]">Feedback Mainbox</h1>

      <div className="mb-4 flex flex-wrap items-end gap-4">
        <div className="min-w-[180px]">
          <div className="mb-1 text-[13px] font-semibold text-gray-500">Open</div>
          <div className="text-lg font-bold text-[#1a1d2e]">{counts.open ?? 0}</div>
        </div>
        <div className="min-w-[180px]">
          <div className="mb-1 text-[13px] font-semibold text-gray-500">Resolved</div>
          <div className="text-lg font-bold text-[#1a1d2e]">{counts.resolved ?? 0}</div>
        </div>
        <div className="min-w-[180px]">
          <div className="mb-1 text-[13px] font-semibold text-gray-500">Total</div>
          <div className="text-lg font-bold text-[#1a1d2e]">{total}</div>
        </div>
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-2 rounded-xl border border-gray-200 bg-white p-4">
        <Input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search…"
          onKeyDown={(e) => { if (e.key === "Enter") { setOffset(0); fetchFeedback(); } }}
          className="min-w-[200px] flex-1"
        />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-auto">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="open">Open</SelectItem>
            <SelectItem value="resolved">Resolved</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" onClick={resetFilters} disabled={!hasFilters}>
          Reset
        </Button>
      </div>

      {loading ? (
        <p className="p-8 text-center text-gray-400">Loading…</p>
      ) : items.length === 0 ? (
        <p className="p-8 text-center text-gray-400">No feedback found.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((item) => (
            <Card key={item.id} className="rounded-xl border border-gray-200 p-5">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <strong className="text-[#1a1d2e]">{item.display_name || item.username}</strong>
                  <span className="text-xs text-gray-400">· {item.email}</span>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={item.status} />
                  <span className="text-xs text-gray-400">{formatTs(item.created_at)}</span>
                </div>
              </div>
              <p className="whitespace-pre-wrap text-[14px] text-[#1a1d2e]">{item.message}</p>
              <div className="mt-2 text-xs text-gray-400">
                QR key: <span className="font-mono">{item.qr_key || "—"}</span>
              </div>
              {item.diagnostics && item.diagnostics.length > 0 && (
                <Diagnostics diag={item.diagnostics} className="mt-2" />
              )}
              {item.admin_reply && (
                <div className="mt-3 rounded-lg bg-blue-50 p-3 text-[13px]">
                  <span className="font-semibold text-[#3b4a6b]">Admin reply:</span>{" "}
                  <span className="text-[#1a1d2e]">{item.admin_reply}</span>
                </div>
              )}
              {item.status === "open" && (
                <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3">
                  <Input
                    type="text"
                    value={replyText[item.id] || ""}
                    onChange={(e) => setReply(item.id, e.target.value)}
                    placeholder="Provide a solution / fix…"
                    disabled={busyId === item.id}
                    onKeyDown={(e) => { if (e.key === "Enter") handleReply(item.id); }}
                    className="min-w-[220px] flex-1"
                  />
                  <Button
                    size="sm"
                    onClick={() => handleReply(item.id)}
                    disabled={busyId === item.id}
                    className="bg-[#3b4a6b] text-white hover:bg-[#34405a]"
                  >
                    {busyId === item.id ? "Saving…" : "Reply & Resolve"}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleResolve(item.id)} disabled={busyId === item.id}>
                    Mark resolved
                  </Button>
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {total > limit && !loading && (
        <div className="mt-4 flex items-center justify-center gap-3">
          <Button variant="outline" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - limit))}>
            Previous
          </Button>
          <span className="text-[13px] text-gray-500">
            {offset + 1}–{Math.min(offset + limit, total)} of {total}
          </span>
          <Button variant="outline" disabled={offset + limit >= total} onClick={() => setOffset((o) => o + limit)}>
            Next
          </Button>
        </div>
      )}
    </Layout>
  );
}