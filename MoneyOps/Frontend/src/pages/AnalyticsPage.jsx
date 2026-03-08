import { useState, useEffect } from "react";
import {
    BarChart3,
    TrendingUp,
    TrendingDown,
    Target,
    Calendar,
    Loader2,
    RefreshCw,
    Info,
} from "lucide-react";
import { toast } from "sonner";
import { InteractiveTrendCard } from "@/components/ui/trend-card";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { useAuth, useUser } from "@clerk/clerk-react";

// ── Fallback Data (only used when API fails) ────────────────────────────────
const FALLBACK_DATA = {
    kpis: [
        { name: "Total Revenue", value: "₹0", trend: "neutral", change: "0%" },
        { name: "Net Profit", value: "₹0", trend: "neutral", change: "0%" },
        { name: "Expenses", value: "₹0", trend: "neutral", change: "0%" },
        { name: "Active Clients", value: "0", trend: "neutral", change: "0%" },
    ],
    revenueByCategory: [],
    monthlyTrends: [
        { month: "Jan", revenue: 0, expenses: 0 },
        { month: "Feb", revenue: 0, expenses: 0 },
        { month: "Mar", revenue: 0, expenses: 0 },
    ],
    clientMetrics: [
        { metric: "Client Retention Rate", value: 0, target: 95, percentage: 0 },
        { metric: "On-time Payment Rate", value: 0, target: 90, percentage: 0 },
        { metric: "Avg Project Value", value: "₹0", target: "₹3.0L", percentage: 0 },
        { metric: "New Leads / Month", value: 0, target: 20, percentage: 0 },
    ],
};

export default function AnalyticsPage() {
    const { userId, orgId } = useOnboardingStatus();
    const { getToken } = useAuth();
    const { user } = useUser();
    const [data, setData] = useState(null);
    const [orgName, setOrgName] = useState("Your Business");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user?.id) {
            fetchAnalytics();
            fetchOrgName();
        }
    }, [orgId, userId, user?.id]);

    const fetchOrgName = async () => {
        if (!userId) return;
        try {
            const res = await fetch(`/api/org/my`, {
                headers: { "X-User-Id": userId, "X-Org-Id": orgId }
            });
            if (res.ok) {
                const result = await res.json();
                setOrgName(result.data?.legalName || "Your Business");
            }
        } catch (err) {
            console.error("Failed to fetch org name", err);
        }
    };

    const fetchAnalytics = async () => {
        try {
            setLoading(true);
            const token = await getToken();
            const headers = {
                "Authorization": `Bearer ${token}`,
                "X-User-Id": user?.id,
                "X-Org-Id": orgId
            };

            // Fetch all data in parallel from our backend
            const [metricsRes, budgetRes, ledgerRes, clientsRes, invoicesRes] = await Promise.all([
                fetch(`/api/finance-intelligence/metrics?businessId=1`, { headers }),
                fetch(`/api/finance-intelligence/budget?businessId=1`, { headers }),
                fetch(`/api/finance-intelligence/ledger?businessId=1`, { headers }),
                fetch(`/api/clients`, { headers }),
                fetch(`/api/invoices`, { headers }),
            ]);

            let metrics = null, budget = null, ledger = null, clients = [], invoices = [];

            if (metricsRes.ok) metrics = await metricsRes.json();
            if (budgetRes.ok) budget = await budgetRes.json();
            if (ledgerRes.ok) ledger = await ledgerRes.json();
            if (clientsRes.ok) {
                const cr = await clientsRes.json();
                clients = cr.data || cr || [];
            }
            if (invoicesRes.ok) {
                const ir = await invoicesRes.json();
                invoices = ir.data || ir || [];
            }

            const revenue = metrics?.revenue || 0;
            const expenses = metrics?.expenses || 0;
            const netProfit = metrics?.netProfit || 0;
            const collectionRate = metrics?.collectionRate || 0;
            const totalClients = Array.isArray(clients) ? clients.length : 0;

            // Build KPIs from real data
            const kpis = [
                { name: "Total Revenue", value: `₹${revenue.toLocaleString("en-IN")}`, trend: revenue > 0 ? "up" : "neutral", change: revenue > 0 ? `+${collectionRate.toFixed(0)}% collected` : "0%" },
                { name: "Net Profit", value: `₹${netProfit.toLocaleString("en-IN")}`, trend: netProfit > 0 ? "up" : netProfit < 0 ? "down" : "neutral", change: revenue > 0 ? `${((netProfit / revenue) * 100).toFixed(1)}% margin` : "0%" },
                { name: "Expenses", value: `₹${expenses.toLocaleString("en-IN")}`, trend: expenses > 0 ? "down" : "neutral", change: revenue > 0 ? `${((expenses / revenue) * 100).toFixed(1)}% of revenue` : "0%" },
                { name: "Active Clients", value: String(totalClients), trend: totalClients > 0 ? "up" : "neutral", change: `${metrics?.totalInvoices || 0} invoices` },
            ];

            // Build revenue by category from budget data
            const budgetItems = budget?.items || [];
            const revenueByCategory = budgetItems.length > 0
                ? budgetItems.map(b => ({
                    category: b.category,
                    amount: b.actual || 0,
                    percentage: budget.totalActual > 0 ? Math.round((b.actual / budget.totalActual) * 100) : 0,
                }))
                : FALLBACK_DATA.revenueByCategory;

            // Build monthly trends from ledger entries
            const entries = ledger?.entries || [];
            const monthMap = {};
            entries.forEach(e => {
                const d = new Date(e.date);
                const key = d.toLocaleString("en-US", { month: "short" });
                if (!monthMap[key]) monthMap[key] = { month: key, revenue: 0, expenses: 0 };
                if (e.type === "INCOME") monthMap[key].revenue += e.amount || 0;
                else monthMap[key].expenses += e.amount || 0;
            });
            const monthlyTrends = Object.values(monthMap).length > 0
                ? Object.values(monthMap)
                : FALLBACK_DATA.monthlyTrends;

            // Build client metrics from real data
            const paidInvoices = metrics?.paidCount || 0;
            const totalInvoices = metrics?.totalInvoices || 0;
            const paymentRate = totalInvoices > 0 ? Math.round((paidInvoices / totalInvoices) * 100) : 0;
            const avgValue = totalClients > 0 ? Math.round(revenue / totalClients) : 0;

            const clientMetrics = [
                { metric: "Collection Rate", value: collectionRate, target: 90, percentage: collectionRate },
                { metric: "On-time Payment Rate", value: paymentRate, target: 90, percentage: paymentRate },
                { metric: "Avg Client Value", value: `₹${avgValue.toLocaleString("en-IN")}`, target: "₹1,00,000", percentage: Math.min(100, Math.round((avgValue / 100000) * 100)) },
                { metric: "Total Invoices", value: totalInvoices, target: 20, percentage: Math.min(100, Math.round((totalInvoices / 20) * 100)) },
            ];

            setData({ kpis, revenueByCategory, monthlyTrends, clientMetrics });
        } catch (error) {
            console.error("Failed to load analytics:", error);
            toast.error("Failed to load analytics data");
            setData(FALLBACK_DATA);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
            </div>
        );
    }

    if (!data) {
        return (
            <div className="flex flex-col items-center justify-center h-96 gap-4">
                <p className="text-[#A0A0A0]">Failed to load analytics data</p>
                <button onClick={fetchAnalytics} className="mo-btn-primary flex items-center gap-2">
                    <RefreshCw className="h-4 w-4" /> Retry
                </button>
            </div>
        );
    }

    const { kpis, revenueByCategory, monthlyTrends, clientMetrics } = data;

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Analytics</h1>
                    <p className="mo-text-secondary mt-1">Performance metrics for {orgName}</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={fetchAnalytics} className="mo-btn-secondary flex items-center gap-2">
                        <RefreshCw className="h-4 w-4" /> Refresh
                    </button>
                    <button className="mo-btn-primary flex items-center gap-2">
                        <BarChart3 className="h-4 w-4" /> Export Report
                    </button>
                </div>
            </div>

            {/* ── KPIs ────────────────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {kpis.map((kpi, index) => (
                    <div key={index} className="mo-stat-card">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-sm text-[#A0A0A0] font-medium">{kpi.name}</span>
                            {kpi.trend === "up" ? (
                                <TrendingUp className="h-4 w-4 text-[#4CBB17]" />
                            ) : kpi.trend === "down" ? (
                                <TrendingDown className="h-4 w-4 text-[#CD1C18]" />
                            ) : (
                                <Info className="h-4 w-4 text-[#A0A0A0]" />
                            )}
                        </div>
                        <div className="text-2xl font-bold text-white">{kpi.value}</div>
                        <p className={`text-xs mt-1 font-medium ${kpi.trend === "up"
                            ? "text-[#4CBB17]"
                            : kpi.trend === "down"
                                ? "text-[#CD1C18]"
                                : "text-[#A0A0A0]"
                            }`}>
                            {kpi.change}
                        </p>
                    </div>
                ))}
            </div>

            {/* ── Charts Row ──────────────────────────────────────────────────── */}
            <div className="grid gap-6 md:grid-cols-2">
                {/* Revenue Trend — InteractiveTrendCard */}
                <InteractiveTrendCard
                    title="Revenue"
                    subtitle="Transaction Trend"
                    totalValue={monthlyTrends.reduce((s, m) => s + m.revenue, 0)}
                    newValue={monthlyTrends[monthlyTrends.length - 1]?.revenue ?? 0}
                    totalValueLabel="Total Revenue"
                    newValueLabel="Last Month"
                    chartData={monthlyTrends.map(m => ({ month: m.month, value: m.revenue }))}
                    defaultBarColor="#2A2A2A"
                    barColor="#4CBB17"
                    adjacentBarColor="#4CBB1760"
                    formatValue={(v) => `₹${v.toLocaleString("en-IN")}`}
                    formatTooltip={(v) => `₹${v.toLocaleString("en-IN")}`}
                />

                {/* Expense Trend — InteractiveTrendCard */}
                <InteractiveTrendCard
                    title="Expenses"
                    subtitle="Transaction Trend"
                    totalValue={monthlyTrends.reduce((s, m) => s + m.expenses, 0)}
                    newValue={monthlyTrends[monthlyTrends.length - 1]?.expenses ?? 0}
                    totalValueLabel="Total Expenses"
                    newValueLabel="Last Month"
                    chartData={monthlyTrends.map(m => ({ month: m.month, value: m.expenses }))}
                    defaultBarColor="#2A2A2A"
                    barColor="#CD1C18"
                    adjacentBarColor="#CD1C1860"
                    formatValue={(v) => `₹${v.toLocaleString("en-IN")}`}
                    formatTooltip={(v) => `₹${v.toLocaleString("en-IN")}`}
                />
            </div>

            {/* ── Expense by Category ──────────────────────────────────────────── */}
            {revenueByCategory.length > 0 && (
                <InteractiveTrendCard
                    title="Expense by Category"
                    subtitle="Breakdown of spending"
                    totalValue={revenueByCategory.reduce((s, c) => s + c.amount, 0)}
                    newValue={Math.max(...revenueByCategory.map(c => c.amount))}
                    totalValueLabel="Total Spend"
                    newValueLabel="Top Category"
                    chartData={revenueByCategory.map(c => ({ month: c.category.slice(0, 4), value: c.amount }))}
                    defaultBarColor="#2A2A2A"
                    barColor="#4CBB17"
                    adjacentBarColor="#4CBB1760"
                    formatValue={(v) => `₹${v.toLocaleString("en-IN")}`}
                    formatTooltip={(v) => `₹${v.toLocaleString("en-IN")}`}
                />
            )}

            {/* ── Client Metrics ───────────────────────────────────────────────── */}
            <div className="mo-card">
                <h2 className="mo-h2 mb-1">Client Performance Metrics</h2>
                <p className="mo-text-secondary mb-6">Track your client-related KPIs and targets</p>
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                    {clientMetrics.map((metric, index) => (
                        <div key={index} className="space-y-3">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-white">{metric.metric}</span>
                                <Target className="h-4 w-4 text-[#A0A0A0]" />
                            </div>
                            <div className="space-y-1.5">
                                <div className="flex justify-between text-sm items-end">
                                    <span className="font-bold text-lg leading-none text-white">
                                        {metric.value}
                                        {metric.metric.includes("Rate") ? "%" : ""}
                                    </span>
                                    <span className="text-xs text-[#A0A0A0]">
                                        Target: {metric.target}
                                        {metric.metric.includes("Rate") ? "%" : ""}
                                    </span>
                                </div>
                                <div className="mo-progress-bg">
                                    <div
                                        className="h-full rounded-full transition-all duration-500"
                                        style={{
                                            width: `${Math.min(metric.percentage, 100)}%`,
                                            backgroundColor:
                                                metric.percentage >= 90
                                                    ? "#4CBB17"
                                                    : metric.percentage >= 70
                                                        ? "#FFB300"
                                                        : "#CD1C18",
                                        }}
                                    />
                                </div>
                                <div className="text-xs text-[#A0A0A0]">
                                    {Math.round(metric.percentage)}% of target achieved
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* ── AI Insights ─────────────────────────────────────────────────── */}
            <div className="mo-card">
                <h2 className="mo-h2 mb-1">AI Insights & Recommendations</h2>
                <p className="mo-text-secondary mb-5">Data-driven insights from your live financial data</p>
                <div className="p-4 bg-[#4CBB1710] border border-[#4CBB1730] rounded-xl flex gap-4 items-start">
                    <div className="bg-[#4CBB1720] p-2 rounded-lg shrink-0">
                        <TrendingUp className="h-5 w-5 text-[#4CBB17]" />
                    </div>
                    <div>
                        <h4 className="font-semibold text-[#4CBB17] text-sm">Live Financial Summary</h4>
                        <p className="text-sm text-[#A0A0A0] mt-1 leading-relaxed">
                            Your collection rate is <strong className="text-white">{(data?.kpis?.[0]?.change) || "N/A"}</strong>.
                            {" "}You have <strong className="text-white">{data?.kpis?.[3]?.value || 0} clients</strong> generating
                            {" "}<strong className="text-white">{data?.kpis?.[0]?.value || "₹0"}</strong> in revenue.
                            Focus on clearing overdue invoices to improve cashflow.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
