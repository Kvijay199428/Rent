import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { api } from '@/services/api';
import { useToast } from '@/hooks/useToast';
import type { DashboardStats } from '@/types';
import {
  TrendingUp,
  TrendingDown,
  Receipt,
  AlertCircle,
  Users,
  Gauge,
  Zap,
  PiggyBank,
  Percent,
  Plus,
  Settings,
  Eye,
  Download,
  Pencil,
  MessageCircle,
  Check,
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import PDFPreviewModal from '@/components/shared/PDFPreviewModal';
import EditBillModal from '@/components/shared/EditBillModal';

const statCards = [
  { key: 'monthly_revenue', label: 'Monthly Revenue', icon: TrendingUp, color: 'bg-blue-500', prefix: '₹' },
  { key: 'prev_monthly_revenue', label: 'Prev Month Revenue', icon: TrendingDown, color: 'bg-gray-500', prefix: '₹' },
  { key: 'paid_bills_count', label: 'Paid Bills', icon: Receipt, color: 'bg-cyan-500', suffix: ' Bills' },
  { key: 'pending_payments_count', label: 'Due Payments', icon: AlertCircle, color: 'bg-red-500', suffix: ' Due' },
  { key: 'pending_amount', label: 'Pending Amount', icon: AlertCircle, color: 'bg-red-600', prefix: '₹' },
  { key: 'amount_collected', label: 'Amount Collected', icon: PiggyBank, color: 'bg-green-500', prefix: '₹' },
  { key: 'active_tenants', label: 'Active Tenants', icon: Users, color: 'bg-blue-600', suffix: ' Active' },
  { key: 'highest_meter_reading', label: 'Last Meter Reading', icon: Gauge, color: 'bg-amber-500', suffix: ' Units' },
  { key: 'electricity_consumed', label: 'Electricity Consumed', icon: Zap, color: 'bg-amber-600', suffix: ' Units' },
  { key: 'collection_rate', label: 'Collection Rate', icon: Percent, color: 'bg-green-600', suffix: '%' },
];

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [previewBill, setPreviewBill] = useState<string | null>(null);
  const [editBill, setEditBill] = useState<string | null>(null);
  const toast = useToast();
  const navigate = useNavigate();

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await api.getDashboardStats();
      setStats(data);
    } catch {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const formatValue = (key: string, value: number) => {
    if (key === 'collection_rate') return value.toFixed(0);
    if (key.includes('revenue') || key.includes('amount') || key.includes('pending')) {
      return '₹' + Math.round(value).toLocaleString('en-IN');
    }
    return value.toLocaleString('en-IN');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!stats) return null;

  const chartLabels = stats.chart_labels ?? [];
  const chartRevenue = stats.chart_revenue ?? [];
  const chartElectricity = stats.chart_electricity ?? [];

  const chartData = chartLabels.map((label, i) => ({
    label,
    revenue: chartRevenue[i] || 0,
    electricity: chartElectricity[i] || 0,
  }));

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <div className="text-sm text-muted-foreground mt-1">
            <span>Today is {today}</span>
            <span className="mx-2">|</span>
            <span>Billing Month: <span className="font-semibold text-primary">{stats.current_month}</span></span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => navigate('/billing')} className="rounded-full">
            <Plus className="h-4 w-4 mr-1" /> New Receipt
          </Button>
          <Button variant="outline" size="icon" onClick={() => navigate('/settings')} className="rounded-full">
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {statCards.map((card) => {
          const value = stats[card.key as keyof DashboardStats] as number;
          return (
            <Card key={card.key} className="overflow-hidden">
              <CardContent className="p-4 relative">
                <div className={`absolute top-3 right-3 w-8 h-8 ${card.color} rounded-lg flex items-center justify-center text-white opacity-90`}>
                  <card.icon size={16} />
                </div>
                <p className="text-xs text-muted-foreground uppercase font-semibold tracking-wider">{card.label}</p>
                <p className="text-xl font-bold mt-1">
                  {formatValue(card.key, value)}
                  {card.suffix && <span className="text-sm font-normal text-muted-foreground">{card.suffix}</span>}
                </p>
                {card.key === 'paid_bills_count' && (
                  <p className="text-xs text-muted-foreground mt-1">{stats.advance_bills_count} In Advance</p>
                )}
                {card.key === 'active_tenants' && (
                  <p className="text-xs text-muted-foreground mt-1">{stats.inactive_tenants} Inactive</p>
                )}
                {card.key === 'prev_monthly_revenue' && (
                  <span className="inline-flex items-center mt-1 px-2 py-0.5 rounded-full text-xs font-medium bg-secondary">
                    {stats.revenue_change_str}
                  </span>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-green-500" /> Revenue Trends
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#22c55e" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)' }}
                  formatter={(value: number) => [`₹${value.toLocaleString('en-IN')}`, 'Revenue']}
                />
                <Area type="monotone" dataKey="revenue" stroke="#22c55e" fill="url(#revGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="h-4 w-4 text-amber-500" /> Electricity Consumption
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="elecGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ background: 'var(--card)', border: '1px solid var(--border)' }}
                  formatter={(value: number) => [`${value} Units`, 'Electricity']}
                />
                <Area type="monotone" dataKey="electricity" stroke="#f59e0b" fill="url(#elecGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Bills */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <Card className="xl:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Receipt className="h-4 w-4 text-primary" /> Recent Bills
            </CardTitle>
            <Button variant="link" size="sm" onClick={() => navigate('/history')}>
              View All
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">S.No</th>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Bill #</th>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Tenant</th>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Month</th>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Total</th>
                    <th className="text-left px-4 py-2 font-medium text-muted-foreground">Payment</th>
                    <th className="text-right px-4 py-2 font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(!stats.recent_bills || stats.recent_bills.length === 0) && (
                    <tr>
                      <td colSpan={7} className="text-center py-8 text-muted-foreground">
                        <Receipt className="h-10 w-10 mx-auto mb-2 opacity-50" />
                        <p>No receipts yet</p>
                        <Button variant="link" onClick={() => navigate('/billing')} className="mt-1">
                          Generate Receipt
                        </Button>
                      </td>
                    </tr>
                  )}
                  {(stats.recent_bills ?? []).map((b, i) => {
                    const grandTotal = b.total + (b.previousArrears || 0);
                    const amtRecv = b.amountReceived || 0;
                    const balanceDue = grandTotal - amtRecv;

                    const statusColors: Record<string, string> = {
                      PAID: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
                      PARTIAL: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
                      ADVANCE: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300',
                      PENDING: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
                    };

                    return (
                      <tr key={b.billNo} className="border-b last:border-0 hover:bg-accent/50 transition-colors">
                        <td className="px-4 py-2 text-muted-foreground">{i + 1}</td>
                        <td className="px-4 py-2">
                          <span className="px-1.5 py-0.5 rounded bg-muted font-mono text-xs">{b.billNo}</span>
                        </td>
                        <td className="px-4 py-2 font-medium text-primary">{b.tenantName}</td>
                        <td className="px-4 py-2 text-muted-foreground">{b.month}</td>
                        <td className="px-4 py-2 font-bold">
                          ₹{b.total.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="px-4 py-2">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusColors[b.paymentStatus] || statusColors.PENDING}`}>
                            {b.paymentStatus === 'PAID' ? <Check size={10} /> : <AlertCircle size={10} />}
                            {b.paymentStatus}
                          </span>
                          <div className="text-xs text-muted-foreground mt-0.5">
                            Recv: ₹{amtRecv.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </div>
                          {balanceDue > 0 && (
                            <div className="text-xs text-red-500 font-medium">
                              Rem: ₹{balanceDue.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                            </div>
                          )}
                        </td>
                        <td className="px-4 py-2">
                          <div className="flex items-center justify-end gap-1">
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setPreviewBill(b.billNo)} title="View">
                              <Eye size={14} />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setEditBill(b.billNo)} title="Edit">
                              <Pencil size={14} className="text-yellow-500" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => {
                              const url = api.getPDFDownloadUrl(b.billNo);
                              const a = document.createElement('a');
                              a.href = url;
                              a.download = `Receipt_${b.billNo}.pdf`;
                              a.click();
                            }} title="Download">
                              <Download size={14} className="text-green-500" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={async () => {
                              try {
                                const data = await api.sendWhatsApp(b.billNo);
                                if (data.url) window.open(data.url, '_blank');
                              } catch { toast.error('Failed'); }
                            }} title="WhatsApp">
                              <MessageCircle size={14} className="text-green-500" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Activity Feed */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-red-500" /> Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { icon: Check, color: 'text-green-500 bg-green-100 dark:bg-green-900/30', title: 'Receipt Generated', desc: 'System automatically saved receipt for tenant', time: '2 hours ago' },
              { icon: Users, color: 'text-blue-500 bg-blue-100 dark:bg-blue-900/30', title: 'Tenant Added', desc: 'New tenant profile created', time: 'Yesterday' },
              { icon: Settings, color: 'text-amber-500 bg-amber-100 dark:bg-amber-900/30', title: 'Settings Updated', desc: 'Billing configuration modified', time: '3 days ago' },
            ].map((item, i) => (
              <div key={i} className="flex gap-3">
                <div className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center ${item.color}`}>
                  <item.icon size={16} />
                </div>
                <div className="flex-1 border-b pb-3 last:border-0">
                  <h6 className="font-semibold text-sm">{item.title}</h6>
                  <p className="text-xs text-muted-foreground">{item.desc}</p>
                  <small className="text-xs text-muted-foreground">{item.time}</small>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <PDFPreviewModal billNo={previewBill} onClose={() => setPreviewBill(null)} />
      <EditBillModal billNo={editBill} onClose={() => setEditBill(null)} onSaved={loadStats} />
    </div>
  );
}
