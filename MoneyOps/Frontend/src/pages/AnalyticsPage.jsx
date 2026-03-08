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
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { InteractiveTrendCard } from "@/components/ui/trend-card";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";

// ── Fallback Data ──────────────────────────────────────────────────────────────
const FALLBACK_DATA = {
    kpis: [
        { name: "Total Revenue", value: "₹12,45,000", trend: "up", change: "+12.5%" },
        { name: "Net Profit", value: "₹4,20,000", trend: "up", change: "+8.2%" },
        { name: "Expenses", value: "₹8,25,000", trend: "down", change: "-2.1%" },
        { name: "Active Clients", value: "42", trend: "neutral", change: "0%" },
    ],
    revenueByCategory: [
        { category: "Consulting", amount: 500000, percentage: 40 },
        { category: "Development", amount: 450000, percentage: 36 },
        { category: "Retainers", amount: 200000, percentage: 16 },
        { category: "Workshops", amount: 95000, percentage: 8 },
    ],
    monthlyTrends: [
        { month: "Jan", revenue: 150000, expenses: 100000 },
        { month: "Feb", revenue: 180000, expenses: 110000 },
        { month: "Mar", revenue: 160000, expenses: 95000 },
        { month: "Apr", revenue: 210000, expenses: 120000 },
        { month: "May", revenue: 190000, expenses: 105000 },
        { month: "Jun", revenue: 240000, expenses: 130000 },
    ],
    clientMetrics: [
        { metric: "Client Retention Rate", value: 92, target: 95, percentage: 92 },
        { metric: "On-time Payment Rate", value: 85, target: 90, percentage: 85 },
        { metric: "Avg Project Value", value: "₹2.5L", target: "₹3.0L", percentage: 83 },
        { metric: "New Leads / Month", value: 15, target: 20, percentage: 75 },
    ],
};

export default function AnalyticsPage() {
    const { userId, orgId } = useOnboardingStatus();
    const [data, setData] = useState(null);
    const [orgName, setOrgName] = useState("Your Business");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAnalytics();
        fetchOrgName();
    }, [orgId, userId]);

    const fetchOrgName = async () => {
        if (!userId) return;
        try {
            const res = await fetch(`/api/org/my`, {
                headers: { "X-User-Id": userId }
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
            await new Promise((resolve) => setTimeout(resolve, 800));
            setData(FALLBACK_DATA);
        } catch (error) {
            console.error(error);
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
                    <button className="mo-btn-secondary flex items-center gap-2">
                        <Calendar className="h-4 w-4" /> Date Range
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
                            {kpi.change} {kpi.trend !== "neutral" && "from last month"}
                        </p>
                    </div>
                ))}
            </div>

            {/* ── Charts Row ──────────────────────────────────────────────────── */}
            <div className="grid gap-6 md:grid-cols-2">
                {/* Revenue Trend — InteractiveTrendCard */}
                <InteractiveTrendCard
                    title="Revenue"
                    subtitle="6-Month Trend"
                    totalValue={data.monthlyTrends.reduce((s, m) => s + m.revenue, 0)}
                    newValue={data.monthlyTrends[data.monthlyTrends.length - 1]?.revenue ?? 0}
                    totalValueLabel="Total Revenue"
                    newValueLabel="Last Month"
                    chartData={data.monthlyTrends.map(m => ({ month: m.month, value: m.revenue }))}
                    defaultBarColor="#2A2A2A"
                    barColor="#4CBB17"
                    adjacentBarColor="#4CBB1760"
                    formatValue={(v) => `₹${v.toLocaleString("en-IN")}`}
                    formatTooltip={(v) => `₹${v.toLocaleString("en-IN")}`}
                />

                {/* Expense Trend — InteractiveTrendCard */}
                <InteractiveTrendCard
                    title="Expenses"
                    subtitle="6-Month Trend"
                    totalValue={data.monthlyTrends.reduce((s, m) => s + m.expenses, 0)}
                    newValue={data.monthlyTrends[data.monthlyTrends.length - 1]?.expenses ?? 0}
                    totalValueLabel="Total Expenses"
                    newValueLabel="Last Month"
                    chartData={data.monthlyTrends.map(m => ({ month: m.month, value: m.expenses }))}
                    defaultBarColor="#2A2A2A"
                    barColor="#CD1C18"
                    adjacentBarColor="#CD1C1860"
                    formatValue={(v) => `₹${v.toLocaleString("en-IN")}`}
                    formatTooltip={(v) => `₹${v.toLocaleString("en-IN")}`}
                />
            </div>

            {/* ── Revenue by Category ──────────────────────────────────────────── */}
            <InteractiveTrendCard
                title="Revenue by Category"
                subtitle="Breakdown of sources"
                totalValue={data.revenueByCategory.reduce((s, c) => s + c.amount, 0)}
                newValue={Math.max(...data.revenueByCategory.map(c => c.amount))}
                totalValueLabel="Total Revenue"
                newValueLabel="Top Category"
                chartData={data.revenueByCategory.map(c => ({ month: c.category.slice(0, 4), value: c.amount }))}
                defaultBarColor="#2A2A2A"
                barColor="#4CBB17"
                adjacentBarColor="#4CBB1760"
                formatValue={(v) => `₹${v.toLocaleString("en-IN")}`}
                formatTooltip={(v) => `₹${v.toLocaleString("en-IN")}`}
            />

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
                <p className="mo-text-secondary mb-5">Data-driven insights to improve your business</p>
                <div className="p-4 bg-[#4CBB1710] border border-[#4CBB1730] rounded-xl flex gap-4 items-start">
                    <div className="bg-[#4CBB1720] p-2 rounded-lg shrink-0">
                        <TrendingUp className="h-5 w-5 text-[#4CBB17]" />
                    </div>
                    <div>
                        <h4 className="font-semibold text-[#4CBB17] text-sm">Projected Growth</h4>
                        <p className="text-sm text-[#A0A0A0] mt-1 leading-relaxed">
                            Based on your current transaction history and invoice clearance rate, your revenue
                            is projected to grow by <strong className="text-white">18%</strong> next month.
                            Consider increasing your retainer capacity to stabilize cash flow.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
