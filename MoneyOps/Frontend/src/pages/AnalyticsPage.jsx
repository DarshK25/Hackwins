import { useState, useEffect } from "react";
import {
    BarChart3,
    TrendingUp,
    TrendingDown,
    Target,
    Loader2,
    RefreshCw,
    Info,
} from "lucide-react";
import { toast } from "sonner";
import { InteractiveTrendCard } from "@/components/ui/trend-card";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { useAuth, useUser } from "@clerk/clerk-react";

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

function monthKey(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function buildLastThreeMonths() {
    const now = new Date();
    const result = [];
    for (let offset = 2; offset >= 0; offset -= 1) {
        const date = new Date(now.getFullYear(), now.getMonth() - offset, 1);
        result.push({
            key: monthKey(date),
            month: date.toLocaleString("en-US", { month: "short" }),
            revenue: 0,
            expenses: 0,
        });
    }
    return result;
}

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
                Authorization: `Bearer ${token}`,
                "X-User-Id": user?.id,
                "X-Org-Id": orgId,
            };

            const [metricsRes, budgetRes, clientsRes, invoicesRes, transactionsRes] = await Promise.all([
                fetch(`/api/finance-intelligence/metrics?businessId=1`, { headers }),
                fetch(`/api/finance-intelligence/budget?businessId=1`, { headers }),
                fetch(`/api/clients`, { headers }),
                fetch(`/api/invoices`, { headers }),
                fetch(`/api/transactions`, { headers }),
            ]);

            let metrics = null;
            let budget = null;
            let clients = [];
            let invoices = [];
            let transactions = [];

            if (metricsRes.ok) metrics = await metricsRes.json();
            if (budgetRes.ok) budget = await budgetRes.json();
            if (clientsRes.ok) {
                const result = await clientsRes.json();
                clients = result.data || result || [];
            }
            if (invoicesRes.ok) {
                const result = await invoicesRes.json();
                invoices = result.data || result || [];
            }
            if (transactionsRes.ok) {
                const result = await transactionsRes.json();
                transactions = result.data || result || [];
            }

            const revenue = Number(metrics?.revenue || 0);
            const expenses = Number(metrics?.expenses || 0);
            const netProfit = Number(metrics?.netProfit || 0);
            const collectionRate = Number(metrics?.collectionRate || 0);
            const totalClients = Array.isArray(clients) ? clients.length : 0;

            const kpis = [
                { name: "Total Revenue", value: `₹${revenue.toLocaleString("en-IN")}`, trend: revenue > 0 ? "up" : "neutral", change: revenue > 0 ? `+${collectionRate.toFixed(0)}% collected` : "0%" },
                { name: "Net Profit", value: `₹${netProfit.toLocaleString("en-IN")}`, trend: netProfit > 0 ? "up" : netProfit < 0 ? "down" : "neutral", change: revenue > 0 ? `${((netProfit / revenue) * 100).toFixed(1)}% margin` : "0%" },
                { name: "Expenses", value: `₹${expenses.toLocaleString("en-IN")}`, trend: expenses > 0 ? "down" : "neutral", change: revenue > 0 ? `${((expenses / revenue) * 100).toFixed(1)}% of revenue` : "0%" },
                { name: "Active Clients", value: String(totalClients), trend: totalClients > 0 ? "up" : "neutral", change: `${metrics?.totalInvoices || 0} invoices` },
            ];

            const budgetItems = budget?.items || [];
            const revenueByCategory = budgetItems.length > 0
                ? budgetItems.map((item) => ({
                    category: item.category,
                    amount: item.actual || 0,
                    percentage: budget.totalActual > 0 ? Math.round((item.actual / budget.totalActual) * 100) : 0,
                }))
                : FALLBACK_DATA.revenueByCategory;

            const trendTemplate = buildLastThreeMonths();
            const trendIndex = Object.fromEntries(trendTemplate.map((item) => [item.key, item]));

            invoices.forEach((invoice) => {
                const key = monthKey(invoice.issueDate || invoice.createdAt || invoice.updatedAt);
                if (!key || !trendIndex[key]) return;
                trendIndex[key].revenue += Number(invoice.totalAmount || invoice.amount || 0);
            });

            transactions.forEach((transaction) => {
                const key = monthKey(transaction.transactionDate || transaction.date || transaction.createdAt);
                if (!key || !trendIndex[key]) return;
                const type = String(transaction.type || "").toUpperCase();
                const amount = Math.abs(Number(transaction.amount || 0));
                if (type === "INCOME") {
                    trendIndex[key].revenue += amount;
                } else {
                    trendIndex[key].expenses += amount;
                }
            });

            const monthlyTrends = trendTemplate.map((item) => ({
                month: item.month,
                revenue: item.revenue,
                expenses: item.expenses,
            }));

            const paidInvoices = Number(metrics?.paidCount || 0);
            const totalInvoices = Number(metrics?.totalInvoices || 0);
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
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Overview</h1>
                    <p className="mo-text-secondary mt-1">Performance metrics for {orgName}</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={fetchAnalytics} className="mo-btn-secondary flex items-center gap-2">
                        <RefreshCw className="h-4 w-4" /> Refresh
                    </button>
                    {/* <button className="mo-btn-primary flex items-center gap-2">
                        <BarChart3 className="h-4 w-4" /> Export Report
                    </button> */}
                </div>
            </div>

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
                        <p className={`text-xs mt-1 font-medium ${kpi.trend === "up" ? "text-[#4CBB17]" : kpi.trend === "down" ? "text-[#CD1C18]" : "text-[#A0A0A0]"}`}>
                            {kpi.change}
                        </p>
                    </div>
                ))}
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                <InteractiveTrendCard
                    title="Revenue"
                    subtitle="Last 3 months"
                    totalValue={monthlyTrends.reduce((sum, month) => sum + month.revenue, 0)}
                    newValue={monthlyTrends[monthlyTrends.length - 1]?.revenue ?? 0}
                    totalValueLabel="3 Month Revenue"
                    newValueLabel="Current Month"
                    chartData={monthlyTrends.map((month) => ({ month: month.month, value: month.revenue }))}
                    defaultBarColor="#2A2A2A"
                    barColor="#4CBB17"
                    adjacentBarColor="#4CBB1760"
                    formatValue={(value) => `₹${value.toLocaleString("en-IN")}`}
                    formatTooltip={(value) => `₹${value.toLocaleString("en-IN")}`}
                />

                <InteractiveTrendCard
                    title="Expenses"
                    subtitle="Last 3 months"
                    totalValue={monthlyTrends.reduce((sum, month) => sum + month.expenses, 0)}
                    newValue={monthlyTrends[monthlyTrends.length - 1]?.expenses ?? 0}
                    totalValueLabel="3 Month Expenses"
                    newValueLabel="Current Month"
                    chartData={monthlyTrends.map((month) => ({ month: month.month, value: month.expenses }))}
                    defaultBarColor="#2A2A2A"
                    barColor="#CD1C18"
                    adjacentBarColor="#CD1C1860"
                    formatValue={(value) => `₹${value.toLocaleString("en-IN")}`}
                    formatTooltip={(value) => `₹${value.toLocaleString("en-IN")}`}
                />
            </div>

            {revenueByCategory.length > 0 && (
                <InteractiveTrendCard
                    title="Expense by Category"
                    subtitle="Breakdown of spending"
                    totalValue={revenueByCategory.reduce((sum, category) => sum + category.amount, 0)}
                    newValue={Math.max(...revenueByCategory.map((category) => category.amount))}
                    totalValueLabel="Total Spend"
                    newValueLabel="Top Category"
                    chartData={revenueByCategory.map((category) => ({ month: category.category.slice(0, 4), value: category.amount }))}
                    defaultBarColor="#2A2A2A"
                    barColor="#4CBB17"
                    adjacentBarColor="#4CBB1760"
                    formatValue={(value) => `₹${value.toLocaleString("en-IN")}`}
                    formatTooltip={(value) => `₹${value.toLocaleString("en-IN")}`}
                />
            )}

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
                                            backgroundColor: metric.percentage >= 90 ? "#4CBB17" : metric.percentage >= 70 ? "#FFB300" : "#CD1C18",
                                        }}
                                    />
                                </div>
                                <div className="text-xs text-[#A0A0A0]">{Math.round(metric.percentage)}% of target achieved</div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            <div className="mo-card">
                <h2 className="mo-h2 mb-1">AI Insights & Recommendations</h2>
                <p className="mo-text-secondary mb-5">Data-driven insights from your live financial data</p>
                <div className="p-4 bg-[#4CBB1710] border border-[#4CBB1730] rounded-xl flex gap-4 items-start">
                    <div className="bg-[#4CBB1720] p-2 rounded-lg shrink-0">
                        <TrendingUp className="h-5 w-5 text-[#4CBB17]" />
                    </div>
                    <div>
                        <h4 className="font-semibold text-[#4CBB17] text-sm">3-month operating view</h4>
                        <p className="text-sm text-[#A0A0A0] mt-1 leading-relaxed">
                            The charts above now track the last three months only, so revenue and expenses reflect a clean recent operating trend instead of a mixed all-time ledger. Use this view to compare billing momentum against actual spending before making growth decisions.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
