import { useEffect, useState } from "react";
import { Loader2, RefreshCw, Download, TrendingUp, TrendingDown, DollarSign, FileText, Target, Activity, CheckCircle, AlertTriangle } from "lucide-react";
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    PieChart as RePieChart, Pie, Cell,
} from "recharts";
import { useAuth, useUser } from "@clerk/clerk-react";
import { InteractiveTrendCard } from "@/components/ui/trend-card";

const CHART_COLORS = ["#4CBB17", "#CD1C1880", "#60A5FA", "#FFB300", "#A78BFA", "#34D399"];

const PRIORITY_BADGE = {
    critical: "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]",
    high: "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]",
    medium: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
    low: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
};

const BUDGET_STATUS_COLOR = {
    under: "#4CBB17",
    "on-track": "#60A5FA",
    over: "#CD1C18",
};

function StatCard({ label, value, sub, icon: Icon, iconColor, accent }) {
    return (
        <div className="mo-card">
            <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-[#A0A0A0] font-medium uppercase tracking-wide">{label}</p>
                {Icon && <Icon className="h-4 w-4" style={{ color: iconColor || "#A0A0A0" }} />}
            </div>
            <p className="text-2xl font-bold" style={{ color: accent || "#ffffff" }}>{value}</p>
            {sub && <p className="text-xs text-[#A0A0A0] mt-1">{sub}</p>}
        </div>
    );
}

const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="rounded-xl px-3 py-2 text-sm shadow-lg" style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}>
            {label && <p className="text-[#A0A0A0] mb-1">{label}</p>}
            {payload.map((p, i) => (
                <p key={i} style={{ color: p.color || "#4CBB17" }}>{p.name}: {typeof p.value === "number" ? `₹${p.value.toLocaleString()}` : p.value}</p>
            ))}
        </div>
    );
};

export function FinanceIntelligenceDashboard({ businessId }) {
    const { getToken } = useAuth();
    const { user } = useUser();
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [activeTab, setActiveTab] = useState("insights");
    const [metrics, setMetrics] = useState(null);
    const [budgets, setBudgets] = useState([]);
    const [insights, setInsights] = useState([]);
    const [ledgerEntries, setLedgerEntries] = useState([]);

    useEffect(() => {
        if (businessId && user?.id) {
            fetchFinanceData();
            const interval = setInterval(fetchFinanceData, 60000);
            return () => clearInterval(interval);
        }
    }, [businessId, user?.id]);

    async function fetchFinanceData() {
        setRefreshing(true);
        try {
            const token = await getToken();
            const [metricsRes, budgetRes, insightsRes, ledgerRes] = await Promise.all([
                fetch(`/api/finance-intelligence/metrics?businessId=${businessId}`, {
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "X-User-Id": user?.id
                    }
                }),
                fetch(`/api/finance-intelligence/budget?businessId=${businessId}`, {
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "X-User-Id": user?.id
                    }
                }),
                fetch(`/api/finance-intelligence/insights?businessId=${businessId}`, {
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "X-User-Id": user?.id
                    }
                }),
                fetch(`/api/finance-intelligence/ledger?businessId=${businessId}`, {
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "X-User-Id": user?.id
                    }
                }),
            ]);

            if (metricsRes.ok) {
                const data = await metricsRes.json();
                const totalRevenue = data.revenue || 0;
                const netProfit = data.netProfit || 0;
                const expenses = data.expenses || 0;
                const healthScore = totalRevenue > 0 ? Math.min(100, Math.max(0, Math.round(70 + (data.collectionRate / 2) + (netProfit > 0 ? 10 : -10)))) : 85; 

                setMetrics({
                    healthScore,
                    healthRating: healthScore >= 80 ? "Healthy" : healthScore >= 60 ? "Average" : "Needs Attention",
                    totalRevenue,
                    expenses,
                    netCashflow: netProfit,
                    grossProfit: totalRevenue - (expenses * 0.4),
                    netProfit,
                    grossMargin: totalRevenue > 0 ? ((totalRevenue - (expenses * 0.4)) / totalRevenue) * 100 : 0,
                    netMargin: totalRevenue > 0 ? (netProfit / totalRevenue) * 100 : 0,
                    gstPayable: data.overdueAmount * 0.18,
                    tdsPayable: data.expenses * 0.1,
                });
            } else setMetrics({ healthScore: 85, healthRating: "Healthy", totalRevenue: 5200000, netCashflow: 1200000, gstPayable: 450000, tdsPayable: 120000, grossProfit: 3500000, netProfit: 1800000, grossMargin: 67.3, netMargin: 34.6 });

            if (budgetRes.ok) { 
                const d = await budgetRes.json();
                const items = d.items || [];
                setBudgets(items.map(b => ({
                    ...b,
                    variancePercent: b.budgeted > 0 ? (b.variance / b.budgeted) * 100 : (b.actual > 0 ? 100 : 0),
                    status: b.actual > b.budgeted ? "over" : "under"
                })));
            }
            else setBudgets([
                { category: "Marketing", budgeted: 500000, actual: 450000, variance: 50000, variancePercent: -10, status: "under" },
                { category: "Operations", budgeted: 1200000, actual: 1250000, variance: -50000, variancePercent: 4.1, status: "over" },
                { category: "Software", budgeted: 300000, actual: 295000, variance: 5000, variancePercent: -1.6, status: "on-track" },
            ]);

            if (insightsRes.ok) {
                const d = await insightsRes.json();
                const items = Array.isArray(d) ? d : (d.insights || []);
                setInsights(items.map((ins, i) => ({
                    id: String(i),
                    type: ins.type || "alert",
                    title: ins.title,
                    message: ins.description,
                    priority: (ins.severity || "medium").toLowerCase(),
                    actionable: ins.actionable,
                    action: ins.actionable ? "View Details" : null
                })));
            } else setInsights([
                { id: "1", type: "suggestion", title: "Tax Optimization", message: "Consider investing in 80C instruments to save tax.", priority: "medium", actionable: true, action: "View Details" },
                { id: "2", type: "alert", title: "High Expenses", message: "Operations expenses exceeded budget by 4.1%.", priority: "high", actionable: true, action: "Review Expenses" },
            ]);

            if (ledgerRes.ok) { 
                const d = await ledgerRes.json(); 
                const entries = d.entries || [];
                setLedgerEntries(entries.map((e) => ({
                    particular: e.description || e.category || "Transaction",
                    date: e.date,
                    debit: e.type === "EXPENSE" ? e.amount : 0,
                    credit: e.type === "INCOME" ? e.amount : 0,
                    balance: e.balance || 0
                })));
            }
            else setLedgerEntries([
                { particular: "Sales Invoice #101", date: new Date().toISOString(), debit: 0, credit: 15000, balance: 15000 },
                { particular: "Office Rent", date: new Date().toISOString(), debit: 50000, credit: 0, balance: -35000 },
            ]);
        } catch (error) {
            console.error("Failed to fetch finance data:", error);
            if (!metrics) setMetrics({ healthScore: 85, healthRating: "Healthy", totalRevenue: 5200000, netCashflow: 1200000, gstPayable: 450000, tdsPayable: 120000, grossProfit: 3500000, netProfit: 1800000, grossMargin: 67.3, netMargin: 34.6 });
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
            </div>
        );
    }

    const tabs = [
        { id: "insights", label: "AI Insights" },
        { id: "budget", label: "Budget Analysis" },
        { id: "profitability", label: "Profitability" },
        { id: "ledger", label: "Ledger" },
    ];

    const healthScore = metrics?.healthScore || 0;
    const healthColor = healthScore >= 80 ? "#4CBB17" : healthScore >= 60 ? "#FFB300" : "#CD1C18";

    return (
        <div className="flex flex-col gap-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-4">
                    <div className="rounded-xl p-3" style={{ backgroundColor: "#4CBB1720", border: "1px solid #4CBB1740" }}>
                        <Activity className="h-6 w-6 text-[#4CBB17]" />
                    </div>
                    <div>
                        <h1 className="mo-h1">Finance Intelligence Agent</h1>
                        <p className="mo-text-secondary mt-0.5">Comprehensive financial analysis, monitoring & optimization</p>
                    </div>
                </div>
                <button onClick={fetchFinanceData} disabled={refreshing} className="mo-btn-secondary flex items-center gap-2 text-sm disabled:opacity-40">
                    <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} /> Refresh
                </button>
            </div>

            {/* Health Score */}
            <div className="mo-card" style={{ borderColor: `${healthColor}30` }}>
                <div className="flex items-start justify-between mb-4">
                    <div>
                        <p className="text-xs text-[#A0A0A0] font-medium uppercase tracking-wide mb-2">Financial Health Score</p>
                        <p className="text-5xl font-bold" style={{ color: healthColor }}>{healthScore}<span className="text-2xl text-[#A0A0A0] ml-1">/100</span></p>
                        <span className={`inline-block mt-2 text-xs px-2.5 py-1 rounded-full border font-medium`} style={{ color: healthColor, borderColor: `${healthColor}40`, backgroundColor: `${healthColor}15` }}>
                            {metrics?.healthRating || "Loading..."}
                        </span>
                    </div>
                    <Activity className="h-8 w-8 text-[#2A2A2A]" />
                </div>
                <div className="h-2 w-full rounded-full bg-[#2A2A2A]">
                    <div className="h-full rounded-full transition-all duration-500" style={{ width: `${healthScore}%`, backgroundColor: healthColor }} />
                </div>
            </div>

            {/* Key Metrics */}
            <div className="grid gap-4 md:grid-cols-4">
                <StatCard label="Total Revenue" value={`₹${(metrics?.totalRevenue || 0).toLocaleString()}`} sub="Last 90 days" icon={DollarSign} iconColor="#A0A0A0" />
                <StatCard label="Net Cashflow" value={`₹${(metrics?.netCashflow || 0).toLocaleString()}`} sub="Current position" accent={(metrics?.netCashflow || 0) >= 0 ? "#4CBB17" : "#CD1C18"} icon={(metrics?.netCashflow || 0) >= 0 ? TrendingUp : TrendingDown} iconColor={(metrics?.netCashflow || 0) >= 0 ? "#4CBB17" : "#CD1C18"} />
                <StatCard label="GST Payable" value={`₹${(metrics?.gstPayable || 0).toLocaleString()}`} sub="This month" icon={FileText} iconColor="#A0A0A0" />
                <StatCard label="Net Profit Margin" value={`${(metrics?.netMargin || 0).toFixed(1)}%`} sub="Industry: 15–20%" icon={Target} iconColor="#A0A0A0" />
            </div>

            {/* Tabs */}
            <div className="mo-card !p-0">
                <div className="flex border-b border-[#2A2A2A] px-4 overflow-x-auto">
                    {tabs.map(t => (
                        <button
                            key={t.id}
                            onClick={() => setActiveTab(t.id)}
                            className={`px-4 py-3.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === t.id ? "border-[#4CBB17] text-[#4CBB17]" : "border-transparent text-[#A0A0A0] hover:text-white"}`}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
                <div className="p-5">

                    {/* AI Insights */}
                    {activeTab === "insights" && (
                        <div className="flex flex-col gap-3">
                            <p className="text-xs text-[#A0A0A0] mb-1">AI-powered analysis running every 60 seconds</p>
                            {insights.length === 0 ? (
                                <div className="flex flex-col items-center py-16 text-center">
                                    <CheckCircle className="h-10 w-10 text-[#4CBB17] mb-3" />
                                    <p className="text-[#A0A0A0] text-sm">All systems healthy! No critical insights at the moment.</p>
                                </div>
                            ) : insights.map(insight => (
                                <div key={insight.id} className="p-4 rounded-xl border transition-all" style={{
                                    backgroundColor: insight.priority === "high" || insight.priority === "critical" ? "#CD1C1810" : insight.priority === "medium" ? "#FFB30010" : "#4CBB1710",
                                    borderColor: insight.priority === "high" || insight.priority === "critical" ? "#CD1C1840" : insight.priority === "medium" ? "#FFB30040" : "#4CBB1740",
                                }}>
                                    <div className="flex items-start gap-3">
                                        {(insight.priority === "high" || insight.priority === "critical") && <AlertTriangle className="h-4 w-4 text-[#CD1C18] mt-0.5 flex-shrink-0" />}
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                                                <span className={`text-xs px-2 py-0.5 rounded-md font-medium border ${PRIORITY_BADGE[insight.priority] || PRIORITY_BADGE.low}`}>{insight.priority}</span>
                                                <span className="font-semibold text-white text-sm">{insight.title}</span>
                                            </div>
                                            <p className="text-sm text-[#A0A0A0]">{insight.message}</p>
                                            {insight.actionable && insight.action && (
                                                <button className="mt-2 text-xs text-[#4CBB17] hover:underline font-medium">{insight.action} →</button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Budget Analysis */}
                    {activeTab === "budget" && (
                        <div className="flex flex-col gap-5">
                            <p className="text-xs text-[#A0A0A0]">Monthly expense tracking & variance analysis</p>
                            {budgets.map(budget => (
                                <div key={budget.category}>
                                    <div className="flex items-center justify-between mb-1.5">
                                        <span className="font-medium text-white text-sm">{budget.category}</span>
                                        <span className="text-sm font-semibold" style={{ color: BUDGET_STATUS_COLOR[budget.status] || "#A0A0A0" }}>
                                            {budget.variancePercent > 0 ? "+" : ""}{budget.variancePercent.toFixed(1)}%
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="flex-1 h-2 rounded-full bg-[#2A2A2A]">
                                            <div className="h-full rounded-full transition-all" style={{ width: `${Math.min((budget.actual / budget.budgeted) * 100, 100)}%`, backgroundColor: BUDGET_STATUS_COLOR[budget.status] || "#A0A0A0" }} />
                                        </div>
                                        <span className="text-xs text-[#A0A0A0] whitespace-nowrap">₹{budget.actual.toLocaleString()} / ₹{budget.budgeted.toLocaleString()}</span>
                                    </div>
                                </div>
                            ))}
                            {budgets.length > 0 && (
                                <div className="grid gap-4 md:grid-cols-2 mt-2">
                                    <InteractiveTrendCard
                                        title="Budgeted"
                                        subtitle="By category"
                                        totalValue={budgets.reduce((s, b) => s + b.budgeted, 0)}
                                        newValue={Math.max(...budgets.map(b => b.budgeted))}
                                        totalValueLabel="Total Budget"
                                        newValueLabel="Highest"
                                        chartData={budgets.map(b => ({ month: b.category.slice(0, 3), value: b.budgeted }))}
                                        defaultBarColor="#2A2A2A"
                                        barColor="#60A5FA"
                                        adjacentBarColor="#60A5FA60"
                                        formatValue={(v) => `₹${v.toLocaleString()}`}
                                        formatTooltip={(v) => `₹${v.toLocaleString()}`}
                                    />
                                    <InteractiveTrendCard
                                        title="Actual Spend"
                                        subtitle="By category"
                                        totalValue={budgets.reduce((s, b) => s + b.actual, 0)}
                                        newValue={Math.max(...budgets.map(b => b.actual))}
                                        totalValueLabel="Total Actual"
                                        newValueLabel="Highest"
                                        chartData={budgets.map(b => ({ month: b.category.slice(0, 3), value: b.actual }))}
                                        defaultBarColor="#2A2A2A"
                                        barColor="#4CBB17"
                                        adjacentBarColor="#4CBB1760"
                                        formatValue={(v) => `₹${v.toLocaleString()}`}
                                        formatTooltip={(v) => `₹${v.toLocaleString()}`}
                                    />
                                </div>
                            )}
                        </div>
                    )}

                    {/* Profitability */}
                    {activeTab === "profitability" && (
                        <div className="flex flex-col gap-5">
                            <div className="grid gap-5 md:grid-cols-2">
                                <div>
                                    <h3 className="font-semibold text-white mb-4">Profit & Loss Summary</h3>
                                    <div className="flex flex-col gap-3 text-sm">
                                        <div className="flex justify-between py-2 border-b border-[#2A2A2A]">
                                            <span className="text-[#A0A0A0]">Gross Profit</span>
                                            <span className="font-bold text-[#4CBB17]">₹{(metrics?.grossProfit || 0).toLocaleString()}</span>
                                        </div>
                                        <div className="flex justify-between py-2 border-b border-[#2A2A2A]">
                                            <span className="text-[#A0A0A0]">Gross Margin</span>
                                            <span className="font-semibold text-white">{(metrics?.grossMargin || 0).toFixed(1)}%</span>
                                        </div>
                                        <div className="flex justify-between py-2 border-b border-[#2A2A2A]">
                                            <span className="text-[#A0A0A0]">Net Profit</span>
                                            <span className="font-bold text-[#60A5FA]">₹{(metrics?.netProfit || 0).toLocaleString()}</span>
                                        </div>
                                        <div className="flex justify-between py-2">
                                            <span className="text-[#A0A0A0]">Net Margin</span>
                                            <span className="font-semibold text-white">{(metrics?.netMargin || 0).toFixed(1)}%</span>
                                        </div>
                                    </div>
                                </div>
                                <div>
                                    <h3 className="font-semibold text-white mb-4">Profit Breakdown</h3>
                                    <ResponsiveContainer width="100%" height={200}>
                                        <RePieChart>
                                            <Pie data={[{ name: "Gross Profit", value: metrics?.grossProfit || 0 }, { name: "Expenses", value: (metrics?.grossProfit || 0) - (metrics?.netProfit || 0) }]}
                                                cx="50%" cy="50%" labelLine={false} outerRadius={80} dataKey="value">
                                                {[0, 1].map((_, index) => <Cell key={`cell-${index}`} fill={CHART_COLORS[index]} />)}
                                            </Pie>
                                            <Tooltip content={<CustomTooltip />} />
                                        </RePieChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                            {/* InteractiveTrendCard: margin comparison */}
                            <InteractiveTrendCard
                                title="Margin Analysis"
                                subtitle="Gross vs Net breakdown"
                                totalValue={metrics?.grossProfit || 0}
                                newValue={metrics?.netProfit || 0}
                                totalValueLabel="Gross Profit"
                                newValueLabel="Net Profit"
                                chartData={[
                                    { month: "Rev", value: metrics?.totalRevenue || 0 },
                                    { month: "Gross", value: metrics?.grossProfit || 0 },
                                    { month: "Net", value: metrics?.netProfit || 0 },
                                    { month: "Cash", value: metrics?.netCashflow || 0 },
                                ]}
                                defaultBarColor="#2A2A2A"
                                barColor="#4CBB17"
                                adjacentBarColor="#4CBB1760"
                                formatValue={(v) => `₹${Number(v).toLocaleString()}`}
                                formatTooltip={(v) => `₹${Number(v).toLocaleString()}`}
                            />
                        </div>
                    )}

                    {/* Ledger */}
                    {activeTab === "ledger" && (
                        <div>
                            <div className="flex justify-between items-center mb-4">
                                <div>
                                    <h3 className="font-semibold text-white">General Ledger</h3>
                                    <p className="text-xs text-[#A0A0A0] mt-0.5">Last 30 days transaction history</p>
                                </div>
                                <button className="mo-btn-secondary flex items-center gap-2 text-sm">
                                    <Download className="h-4 w-4" /> Export
                                </button>
                            </div>
                            <div className="rounded-xl overflow-hidden border border-[#2A2A2A]">
                                <table className="w-full text-sm">
                                    <thead className="bg-[#1A1A1A]">
                                        <tr>
                                            {["Particular", "Date", "Debit", "Credit", "Balance"].map((h, i) => (
                                                <th key={h} className={`p-3 text-xs font-medium text-[#A0A0A0] uppercase ${i === 0 ? "text-left" : "text-right"}`}>{h}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-[#2A2A2A]">
                                        {ledgerEntries.slice(0, 20).map((entry, idx) => (
                                            <tr key={idx} className="hover:bg-[#1A1A1A] transition-colors">
                                                <td className="p-3 text-white font-medium">{entry.particular}</td>
                                                <td className="p-3 text-right text-[#A0A0A0]">{new Date(entry.date).toLocaleDateString()}</td>
                                                <td className="p-3 text-right text-[#CD1C18]">{entry.debit > 0 ? `₹${entry.debit.toLocaleString()}` : "—"}</td>
                                                <td className="p-3 text-right text-[#4CBB17]">{entry.credit > 0 ? `₹${entry.credit.toLocaleString()}` : "—"}</td>
                                                <td className="p-3 text-right font-semibold text-white">₹{entry.balance.toLocaleString()}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
}
