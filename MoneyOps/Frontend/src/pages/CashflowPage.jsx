import { useEffect, useMemo, useState } from "react";
import { TrendingUp, TrendingDown, AlertTriangle, Calendar, Loader2 } from "lucide-react";
import { useAuth, useUser } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";

const FORECAST_WINDOWS = [7, 30, 90];

const PRIORITY_BADGE = {
    high: "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]",
    medium: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
    low: "bg-[#A0A0A020] text-[#A0A0A0] border-[#A0A0A040]",
};

function formatInr(value) {
    return `₹${Number(value || 0).toLocaleString("en-IN")}`;
}

function toIsoDate(value) {
    return String(value || "").slice(0, 10);
}

function daysUntil(value) {
    if (!value) return null;
    const target = new Date(value);
    const today = new Date();
    target.setHours(0, 0, 0, 0);
    today.setHours(0, 0, 0, 0);
    return Math.round((target - today) / 86400000);
}

export default function CashflowPage() {
    const { getToken } = useAuth();
    const { user } = useUser();
    const { orgId } = useOnboardingStatus();
    const [loading, setLoading] = useState(true);
    const [cashFlowData, setCashFlowData] = useState({
        invoices: [],
        transactions: [],
        metrics: {},
    });

    useEffect(() => {
        if (user?.id && orgId) {
            fetchCashFlow();
        }
    }, [user?.id, orgId]);

    async function fetchCashFlow() {
        setLoading(true);
        try {
            const token = await getToken();
            const headers = {
                Authorization: `Bearer ${token}`,
                "X-User-Id": user?.id,
                "X-Org-Id": orgId,
            };

            const [invoicesRes, transactionsRes, metricsRes] = await Promise.all([
                fetch("/api/invoices", { headers }),
                fetch("/api/transactions", { headers }),
                fetch("/api/finance-intelligence/metrics?businessId=1", { headers }),
            ]);

            const invoicesJson = invoicesRes.ok ? await invoicesRes.json() : [];
            const transactionsJson = transactionsRes.ok ? await transactionsRes.json() : [];
            const metricsJson = metricsRes.ok ? await metricsRes.json() : {};

            setCashFlowData({
                invoices: Array.isArray(invoicesJson) ? invoicesJson : invoicesJson.data || [],
                transactions: Array.isArray(transactionsJson) ? transactionsJson : transactionsJson.content || transactionsJson.transactions || [],
                metrics: metricsJson || {},
            });
        } finally {
            setLoading(false);
        }
    }

    const { forecastData, upcomingPayments, expectedIncome, insights } = useMemo(() => {
        const invoices = cashFlowData.invoices || [];
        const transactions = cashFlowData.transactions || [];
        const metrics = cashFlowData.metrics || {};
        const now = new Date();

        const openInvoices = invoices
            .filter((invoice) => !["PAID", "CANCELLED"].includes(String(invoice.status || "").toUpperCase()))
            .map((invoice) => {
                const total = Number(invoice.totalAmount || 0);
                const paid = Number(invoice.paidAmount || 0);
                const outstanding = Math.max(0, total - paid);
                return {
                    id: invoice.id,
                    description: `${invoice.clientName || "Client"} - ${invoice.invoiceNumber || "Invoice"}`,
                    amount: outstanding,
                    dueDate: toIsoDate(invoice.dueDate),
                    priority: (daysUntil(invoice.dueDate) ?? 0) < 0 ? "high" : (daysUntil(invoice.dueDate) ?? 0) <= 7 ? "medium" : "low",
                };
            })
            .sort((a, b) => new Date(a.dueDate || now).getTime() - new Date(b.dueDate || now).getTime());

        const expenseTransactions = transactions
            .filter((txn) => String(txn.type || "").toUpperCase() === "EXPENSE")
            .map((txn) => ({
                id: txn.id,
                description: txn.description || txn.vendorName || "Expense",
                amount: Math.abs(Number(txn.amount || 0)),
                dueDate: toIsoDate(txn.transactionDate || txn.date || txn.createdAt),
                priority: "medium",
            }))
            .sort((a, b) => new Date(b.dueDate || now).getTime() - new Date(a.dueDate || now).getTime())
            .slice(0, 5);

        const inflowCandidates = openInvoices.slice(0, 5);
        const monthlyExpenses = Number(metrics.expenses || 0);

        const derivedForecast = FORECAST_WINDOWS.map((days) => {
            const inflow = openInvoices
                .filter((invoice) => {
                    const delta = daysUntil(invoice.dueDate);
                    return delta !== null && delta <= days;
                })
                .reduce((sum, invoice) => sum + invoice.amount, 0);
            const outflow = Math.round((monthlyExpenses / 30) * days);
            return {
                period: `Next ${days} days`,
                inflow,
                outflow,
                net: inflow - outflow,
                status: inflow - outflow >= 0 ? "positive" : "tight",
            };
        });

        const derivedInsights = [];
        const overdueAmount = Number(metrics.overdueAmount || 0);
        const overdueCount = Number(metrics.overdueCount || 0);
        const revenue = Number(metrics.revenue || 0);
        const expenseRatio = revenue > 0 ? monthlyExpenses / revenue : 0;

        if (overdueCount > 0) {
            derivedInsights.push({
                border: "#CD1C1840",
                bg: "#CD1C1810",
                title: "Collection Risk",
                titleColor: "#CD1C18",
                body: `${overdueCount} overdue invoice${overdueCount > 1 ? "s are" : " is"} tying up ${formatInr(overdueAmount)}. Collection speed is your biggest cashflow lever right now.`,
            });
        }
        if (expenseRatio > 0.5) {
            derivedInsights.push({
                border: "#FFB30040",
                bg: "#FFB30010",
                title: "Expense Watch",
                titleColor: "#FFB300",
                body: `Operating expenses are ${Math.round(expenseRatio * 100)}% of revenue. Review large recurring outflows before they compress liquidity.`,
            });
        } else {
            derivedInsights.push({
                border: "#4CBB1740",
                bg: "#4CBB1710",
                title: "Healthy Margin",
                titleColor: "#4CBB17",
                body: `Expense load is only ${Math.round(expenseRatio * 100)}% of revenue. That leaves room to fund growth without immediate cash stress.`,
            });
        }
        derivedInsights.push({
            border: "#60A5FA40",
            bg: "#60A5FA10",
            title: "Signal",
            titleColor: "#60A5FA",
            body: inflowCandidates.length
                ? `Expected collections are led by ${inflowCandidates[0].description} at ${formatInr(inflowCandidates[0].amount)}. Prioritize that follow-up first.`
                : "No open invoices are available to project near-term inflows yet.",
        });

        return {
            forecastData: derivedForecast,
            upcomingPayments: expenseTransactions,
            expectedIncome: inflowCandidates,
            insights: derivedInsights,
        };
    }, [cashFlowData]);

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Cash Flow</h1>
                    <p className="mo-text-secondary mt-1">Monitor and forecast your business cashflow</p>
                </div>
                <div className="flex gap-2">
                    <button className="mo-btn-secondary flex items-center gap-2" disabled>
                        <Calendar className="h-4 w-4" /> Schedule Payments
                    </button>
                    <button className="mo-btn-primary flex items-center gap-2" onClick={fetchCashFlow}>
                        <TrendingUp className="h-4 w-4" /> Refresh Forecast
                    </button>
                </div>
            </div>

            {/* ── Forecast Cards ─────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-3">
                {forecastData.map((forecast, index) => (
                    <div key={index} className="mo-stat-card">
                        <div className="flex items-center justify-between mb-4">
                            <span className="text-sm font-semibold text-white">{forecast.period}</span>
                            <span className="text-xs px-2 py-0.5 rounded-md font-medium bg-[#4CBB1720] text-[#4CBB17] border border-[#4CBB1740]">
                                {forecast.status}
                            </span>
                        </div>
                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-[#A0A0A0]">Inflow</span>
                                <span className="font-medium text-[#4CBB17]">{formatInr(forecast.inflow)}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-[#A0A0A0]">Outflow</span>
                                <span className="font-medium text-[#CD1C18]">{formatInr(forecast.outflow)}</span>
                            </div>
                            <div className="flex justify-between text-base font-bold border-t border-[#2A2A2A] pt-3 mt-1">
                                <span className="text-white">Net</span>
                                <span style={{ color: forecast.net >= 0 ? "#4CBB17" : "#CD1C18" }}>
                                    {formatInr(forecast.net)}
                                </span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* ── Payments & Income ──────────────────────────────────────────── */}
            <div className="grid gap-6 md:grid-cols-2">
                {/* Upcoming Payments */}
                <div className="mo-card">
                    <div className="flex items-center gap-2 mb-4">
                        <TrendingDown className="h-5 w-5 text-[#CD1C18]" />
                        <div>
                            <h2 className="mo-h2">Upcoming Payments</h2>
                            <p className="mo-text-secondary">Scheduled outgoing payments</p>
                        </div>
                    </div>
                    <div className="space-y-2">
                        {upcomingPayments.length === 0 && (
                            <p className="text-sm text-[#A0A0A0]">No recent expense transactions found.</p>
                        )}
                        {upcomingPayments.map((payment) => (
                            <div
                                key={payment.id}
                                className="flex items-center justify-between p-3 rounded-xl border border-[#2A2A2A] bg-[#111111] hover:border-[#3A3A3A] transition-colors"
                            >
                                <div className="flex-1 min-w-0 mr-3">
                                    <p className="font-medium text-white text-sm truncate">{payment.description}</p>
                                    <p className="text-xs text-[#A0A0A0] mt-0.5">Date: {payment.dueDate || "Not set"}</p>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                    <span className={`text-xs px-2 py-0.5 rounded-md font-medium border ${PRIORITY_BADGE[payment.priority]}`}>
                                        {payment.priority}
                                    </span>
                                    <span className="font-bold text-[#CD1C18] text-sm">
                                        {formatInr(payment.amount)}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Expected Income */}
                <div className="mo-card">
                    <div className="flex items-center gap-2 mb-4">
                        <TrendingUp className="h-5 w-5 text-[#4CBB17]" />
                        <div>
                            <h2 className="mo-h2">Expected Income</h2>
                            <p className="mo-text-secondary">Anticipated incoming payments</p>
                        </div>
                    </div>
                    <div className="space-y-2">
                        {expectedIncome.length === 0 && (
                            <p className="text-sm text-[#A0A0A0]">No unpaid invoices available for near-term inflow projection.</p>
                        )}
                        {expectedIncome.map((income) => (
                            <div
                                key={income.id}
                                className="flex items-center justify-between p-3 rounded-xl border border-[#2A2A2A] bg-[#111111] hover:border-[#3A3A3A] transition-colors"
                            >
                                <div className="flex-1 min-w-0 mr-3">
                                    <p className="font-medium text-white text-sm truncate">{income.description}</p>
                                    <p className="text-xs text-[#A0A0A0] mt-0.5">Expected: {income.dueDate || "Not set"}</p>
                                </div>
                                <span className="font-bold text-[#4CBB17] text-sm flex-shrink-0">
                                    {formatInr(income.amount)}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* ── AI Insights ──────────────────────────────────────────────────── */}
            <div className="mo-card">
                <div className="flex items-center gap-2 mb-5">
                    <AlertTriangle className="h-5 w-5 text-[#FFB300]" />
                    <div>
                        <h2 className="mo-h2">Cashflow Insights</h2>
                        <p className="mo-text-secondary">Derived from live invoices, transactions, and finance metrics</p>
                    </div>
                </div>
                <div className="grid gap-4 md:grid-cols-3">
                    {insights.map(({ border, bg, title, titleColor, body }) => (
                        <div
                            key={title}
                            className="p-4 rounded-xl border"
                            style={{ borderColor: border, backgroundColor: bg }}
                        >
                            <h4 className="font-semibold text-sm mb-1.5" style={{ color: titleColor }}>{title}</h4>
                            <p className="text-sm text-[#A0A0A0] leading-relaxed">{body}</p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
