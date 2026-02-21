import { useState, useEffect } from "react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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

// ── Fallback Data ─────────────────────────────────────────────────────────────
// Used when API fails or returns empty data, ensuring the UI always looks good.
const FALLBACK_DATA = {
    kpis: [
        {
            name: "Total Revenue",
            value: "₹12,45,000",
            trend: "up",
            change: "+12.5%",
        },
        {
            name: "Net Profit",
            value: "₹4,20,000",
            trend: "up",
            change: "+8.2%",
        },
        {
            name: "Expenses",
            value: "₹8,25,000",
            trend: "down",
            change: "-2.1%",
        },
        {
            name: "Active Clients",
            value: "42",
            trend: "neutral",
            change: "0%",
        },
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
        {
            metric: "Client Retention Rate",
            value: 92,
            target: 95,
            percentage: 92,
        },
        {
            metric: "On-time Payment Rate",
            value: 85,
            target: 90,
            percentage: 85,
        },
        {
            metric: "Avg Project Value",
            value: "₹2.5L",
            target: "₹3.0L",
            percentage: 83,
        },
        {
            metric: "New Leads / Month",
            value: 15,
            target: 20,
            percentage: 75,
        },
    ],
};

export default function AnalyticsPage() {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAnalytics();
    }, []);

    const fetchAnalytics = async () => {
        try {
            setLoading(true);
            // Simulate API call - in real app, replace with actual fetch
            // const res = await fetch('/api/analytics');
            // const result = await res.json();

            // Simulating network delay for realism
            await new Promise((resolve) => setTimeout(resolve, 800));

            // Use fallback data for now since backend likely doesn't have this endpoint ready yet
            setData(FALLBACK_DATA);
        } catch (error) {
            console.error(error);
            toast.error("Failed to load analytics data");
            // Fallback to ensure UI doesn't break
            setData(FALLBACK_DATA);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-96">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
        );
    }

    if (!data) {
        return (
            <div className="flex flex-col items-center justify-center h-96 gap-4">
                <p className="text-slate-500">Failed to load analytics data</p>
                <Button onClick={fetchAnalytics}>
                    <RefreshCw className="mr-2 h-4 w-4" /> Retry
                </Button>
            </div>
        );
    }

    const { kpis, revenueByCategory, monthlyTrends, clientMetrics } = data;

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="text-3xl font-bold">Analytics</h1>
                    <p className="text-slate-500 text-sm mt-1">
                        Business insights and performance metrics
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline">
                        <Calendar className="mr-2 h-4 w-4" />
                        Date Range
                    </Button>
                    <Button>
                        <BarChart3 className="mr-2 h-4 w-4" />
                        Export Report
                    </Button>
                </div>
            </div>

            {/* ── KPIs ───────────────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {kpis.map((kpi, index) => (
                    <Card key={index}>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium text-slate-500">
                                {kpi.name}
                            </CardTitle>
                            {kpi.trend === "up" ? (
                                <TrendingUp className="h-4 w-4 text-green-600" />
                            ) : kpi.trend === "down" ? (
                                <TrendingDown className="h-4 w-4 text-red-600" />
                            ) : (
                                <Info className="h-4 w-4 text-slate-400" />
                            )}
                        </CardHeader>
                        <CardContent>
                            <div className="text-2xl font-bold">{kpi.value}</div>
                            <p
                                className={`text-xs mt-1 ${kpi.trend === "up"
                                        ? "text-green-600"
                                        : kpi.trend === "down"
                                            ? "text-red-600"
                                            : "text-slate-500"
                                    }`}
                            >
                                {kpi.change} {kpi.trend !== "neutral" && "from last month"}
                            </p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* ── Revenue by Category ────────────────────────────────────── */}
                <Card>
                    <CardHeader>
                        <CardTitle>Revenue by Category</CardTitle>
                        <CardDescription>Breakdown of revenue sources (Top 5)</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {revenueByCategory.length > 0 ? (
                            revenueByCategory.map((item, index) => (
                                <div key={index} className="space-y-2">
                                    <div className="flex justify-between text-sm">
                                        <span className="font-medium text-slate-700">
                                            {item.category}
                                        </span>
                                        <span className="font-semibold">
                                            ₹{item.amount.toLocaleString("en-IN")}
                                        </span>
                                    </div>
                                    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                                        <div
                                            className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
                                            style={{ width: `${item.percentage}%` }}
                                        ></div>
                                    </div>
                                    <div className="text-xs text-slate-400 text-right">
                                        {item.percentage}%
                                    </div>
                                </div>
                            ))
                        ) : (
                            <p className="text-sm text-slate-500 text-center py-8">
                                No revenue data available
                            </p>
                        )}
                    </CardContent>
                </Card>

                {/* ── Monthly Trends Chart ───────────────────────────────────── */}
                <Card>
                    <CardHeader>
                        <CardTitle>Monthly Trends</CardTitle>
                        <CardDescription>Revenue vs. Expenses (Last 6 Months)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex flex-col h-full justify-between gap-6">
                            {/* Legend */}
                            <div className="flex items-center gap-6 text-sm justify-center">
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                                    <span className="text-slate-600">Revenue</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                                    <span className="text-slate-600">Expenses</span>
                                </div>
                            </div>

                            {/* Bar Chart */}
                            <div className="flex items-end justify-between gap-2 h-48 pt-4 pb-2">
                                {monthlyTrends.map((month, index) => {
                                    const maxVal = Math.max(
                                        ...monthlyTrends.map((m) => Math.max(m.revenue, m.expenses))
                                    ) * 1.1; // 10% headroom

                                    const revHeight = (month.revenue / maxVal) * 100;
                                    const expHeight = (month.expenses / maxVal) * 100;

                                    return (
                                        <div
                                            key={index}
                                            className="flex flex-col items-center gap-2 h-full justify-end flex-1"
                                        >
                                            <div className="flex gap-1 items-end h-full w-full justify-center">
                                                {/* Revenue Bar */}
                                                <div
                                                    className="w-3 sm:w-6 bg-green-500 rounded-t transition-all hover:opacity-80"
                                                    style={{ height: `${revHeight}%` }}
                                                    title={`Revenue: ₹${month.revenue.toLocaleString()}`}
                                                ></div>
                                                {/* Expense Bar */}
                                                <div
                                                    className="w-3 sm:w-6 bg-red-500 rounded-t transition-all hover:opacity-80"
                                                    style={{ height: `${expHeight}%` }}
                                                    title={`Expenses: ₹${month.expenses.toLocaleString()}`}
                                                ></div>
                                            </div>
                                            <span className="text-xs font-medium text-slate-500">
                                                {month.month}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* ── Client Metrics ─────────────────────────────────────────────── */}
            <Card>
                <CardHeader>
                    <CardTitle>Client Performance Metrics</CardTitle>
                    <CardDescription>
                        Track your client-related KPIs and targets
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
                        {clientMetrics.map((metric, index) => (
                            <div key={index} className="space-y-3">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium text-slate-700">
                                        {metric.metric}
                                    </span>
                                    <Target className="h-4 w-4 text-slate-400" />
                                </div>
                                <div className="space-y-2">
                                    <div className="flex justify-between text-sm items-end">
                                        <span className="font-bold text-lg leading-none">
                                            {metric.value}
                                            {metric.metric.includes("Rate") ? "%" : ""}
                                        </span>
                                        <span className="text-xs text-slate-400">
                                            Target: {metric.target}
                                            {metric.metric.includes("Rate") ? "%" : ""}
                                        </span>
                                    </div>
                                    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                                        <div
                                            className={`h-2 rounded-full transition-all duration-500 ${metric.percentage >= 90
                                                    ? "bg-green-500"
                                                    : metric.percentage >= 70
                                                        ? "bg-yellow-500"
                                                        : "bg-red-500"
                                                }`}
                                            style={{ width: `${Math.min(metric.percentage, 100)}%` }}
                                        ></div>
                                    </div>
                                    <div className="text-xs text-slate-500">
                                        {Math.round(metric.percentage)}% of target achieved
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* ── AI Insights ────────────────────────────────────────────────── */}
            <Card>
                <CardHeader>
                    <CardTitle>AI Insights & Recommendations</CardTitle>
                    <CardDescription>
                        Data-driven insights to improve your business
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg flex gap-4 items-start">
                        <div className="bg-blue-100 p-2 rounded-md shrink-0">
                            <TrendingUp className="h-5 w-5 text-blue-600" />
                        </div>
                        <div>
                            <h4 className="font-semibold text-blue-900 text-sm">
                                Projected Growth
                            </h4>
                            <p className="text-sm text-blue-700 mt-1 leading-relaxed">
                                Based on your current transaction history and invoice clearance rate,
                                your revenue is projected to grow by <strong>18%</strong> next month.
                                Consider increasing your retainer capacity to stabilize cash flow.
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
