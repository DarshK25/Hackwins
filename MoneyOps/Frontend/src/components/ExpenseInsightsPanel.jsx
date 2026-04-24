import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, PieChart, TrendingDown, TrendingUp, Wallet } from "lucide-react";

function formatMoney(value) {
    return `Rs ${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function percent(value, total) {
    if (!total) {
        return 0;
    }
    return Number(((Number(value || 0) / Number(total || 0)) * 100).toFixed(1));
}

export default function ExpenseInsightsPanel({ orgId, buildHeaders, expenseSummary, period, refreshToken }) {
    const [loading, setLoading] = useState(true);
    const [overviewMetrics, setOverviewMetrics] = useState(null);
    const [budgets, setBudgets] = useState([]);
    const [error, setError] = useState("");

    useEffect(() => {
        let isMounted = true;

        async function loadInsights() {
            if (!orgId) {
                return;
            }

            try {
                setLoading(true);
                setError("");
                const headers = await buildHeaders();
                const [overviewResponse, budgetResponse] = await Promise.all([
                    fetch(`/api/overview/metrics?orgId=${encodeURIComponent(orgId)}&period=${encodeURIComponent(period)}`, { headers }),
                    fetch(`/api/budgets?orgId=${encodeURIComponent(orgId)}`, { headers }),
                ]);

                if (!overviewResponse.ok) {
                    throw new Error("Failed to load overview metrics");
                }

                const overviewPayload = await overviewResponse.json();
                const budgetPayload = budgetResponse.ok ? await budgetResponse.json() : [];

                if (!isMounted) {
                    return;
                }

                setOverviewMetrics(overviewPayload?.data || overviewPayload || null);
                setBudgets(Array.isArray(budgetPayload) ? budgetPayload : budgetPayload?.data || []);
            } catch (requestError) {
                if (!isMounted) {
                    return;
                }
                setOverviewMetrics(null);
                setBudgets([]);
                setError(requestError.message || "Failed to load insights");
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        }

        loadInsights();
        return () => {
            isMounted = false;
        };
    }, [orgId, buildHeaders, period, refreshToken]);

    const insightModel = useMemo(() => {
        const revenue = Number(overviewMetrics?.totalRevenue || 0);
        const expenses = Number(overviewMetrics?.totalExpenses || expenseSummary?.totalExpenses || 0);
        const netProfitLoss = Number(overviewMetrics?.netProfitLoss || (revenue - expenses));
        const profitMargin = percent(netProfitLoss, revenue);
        const expenseRatio = percent(expenses, revenue);

        const today = new Date();
        const activeBudgets = (budgets || []).filter((budget) => {
            if (!budget?.startDate || !budget?.endDate) {
                return false;
            }
            const startDate = new Date(budget.startDate);
            const endDate = new Date(budget.endDate);
            return startDate <= today && endDate >= today;
        });

        const budgetTotals = activeBudgets.reduce((accumulator, budget) => {
            accumulator.totalBudget += Number(budget.totalBudget || 0);
            accumulator.totalSpent += Number(budget.totalSpent || 0);
            return accumulator;
        }, { totalBudget: 0, totalSpent: 0 });

        const budgetUtilization = percent(budgetTotals.totalSpent, budgetTotals.totalBudget);
        const topCategories = (expenseSummary?.byCategory || []).slice(0, 3);
        const trend = expenseSummary?.trend || [];
        const previousPoint = trend.length > 1 ? trend[trend.length - 2] : null;
        const latestPoint = trend.length > 0 ? trend[trend.length - 1] : null;
        const monthOverMonth = previousPoint && latestPoint
            ? percent(Number(latestPoint.total || 0) - Number(previousPoint.total || 0), Number(previousPoint.total || 0))
            : 0;

        const alerts = [];
        if (expenseRatio > 70) {
            alerts.push(`Expense ratio is ${expenseRatio}% of revenue, which is above the 70% alert threshold.`);
        }
        if (budgetTotals.totalBudget > 0 && budgetUtilization > 80) {
            alerts.push(`Active budgets are ${budgetUtilization}% utilized. Consider reviewing high-spend categories.`);
        }
        if (monthOverMonth > 15) {
            alerts.push(`Expenses are up ${monthOverMonth}% versus the previous period.`);
        }

        return {
            revenue,
            expenses,
            netProfitLoss,
            profitMargin,
            expenseRatio,
            budgetUtilization,
            topCategories,
            monthOverMonth,
            alerts,
            hasBudget: budgetTotals.totalBudget > 0,
        };
    }, [overviewMetrics, budgets, expenseSummary]);

    if (loading) {
        return (
            <div className="mo-card animate-pulse">
                <div className="h-5 w-40 rounded bg-[#1F1F1F]" />
                <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    {[1, 2, 3, 4].map((item) => (
                        <div key={item} className="h-28 rounded-2xl bg-[#111111]" />
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="mo-card">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <h2 className="mo-h2">Expense Insights</h2>
                    <p className="mo-text-secondary mt-1">
                        Live recalculation of profitability, spend pressure, and budget usage.
                    </p>
                </div>
                {error ? <div className="text-sm text-[#F87171]">{error}</div> : null}
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl border border-[#242424] bg-[#111111] p-4">
                    <div className="flex items-center justify-between text-sm text-[#A0A0A0]">
                        <span>Profit Margin</span>
                        <TrendingUp className="h-4 w-4 text-[#4CBB17]" />
                    </div>
                    <div className="mt-3 text-2xl font-semibold text-white">{insightModel.profitMargin}%</div>
                    <div className="mt-2 text-xs text-[#A0A0A0]">
                        Net profit/loss {formatMoney(insightModel.netProfitLoss)}
                    </div>
                </div>

                <div className="rounded-2xl border border-[#242424] bg-[#111111] p-4">
                    <div className="flex items-center justify-between text-sm text-[#A0A0A0]">
                        <span>Expense Ratio</span>
                        <TrendingDown className="h-4 w-4 text-[#FFB300]" />
                    </div>
                    <div className="mt-3 text-2xl font-semibold text-white">{insightModel.expenseRatio}%</div>
                    <div className="mt-2 text-xs text-[#A0A0A0]">
                        Expenses {formatMoney(insightModel.expenses)} vs revenue {formatMoney(insightModel.revenue)}
                    </div>
                </div>

                <div className="rounded-2xl border border-[#242424] bg-[#111111] p-4">
                    <div className="flex items-center justify-between text-sm text-[#A0A0A0]">
                        <span>Budget Utilization</span>
                        <Wallet className="h-4 w-4 text-[#60A5FA]" />
                    </div>
                    <div className="mt-3 text-2xl font-semibold text-white">
                        {insightModel.hasBudget ? `${insightModel.budgetUtilization}%` : "--"}
                    </div>
                    <div className="mt-2 text-xs text-[#A0A0A0]">
                        {insightModel.hasBudget ? "Across active budgets" : "No active budget found"}
                    </div>
                </div>

                <div className="rounded-2xl border border-[#242424] bg-[#111111] p-4">
                    <div className="flex items-center justify-between text-sm text-[#A0A0A0]">
                        <span>Month-over-Month</span>
                        <PieChart className="h-4 w-4 text-[#4CBB17]" />
                    </div>
                    <div className="mt-3 text-2xl font-semibold text-white">{insightModel.monthOverMonth}%</div>
                    <div className="mt-2 text-xs text-[#A0A0A0]">
                        Change versus the previous point in the expense trend
                    </div>
                </div>
            </div>

            <div className="mt-5 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
                <div className="rounded-2xl border border-[#242424] bg-[#111111] p-4">
                    <div className="text-sm font-semibold text-white">Top Spending Categories</div>
                    <div className="mt-3 space-y-3">
                        {insightModel.topCategories.length === 0 ? (
                            <div className="text-sm text-[#A0A0A0]">No categorized expenses yet.</div>
                        ) : (
                            insightModel.topCategories.map((category) => (
                                <div key={category.category} className="rounded-xl border border-[#1D1D1D] bg-[#0C0C0C] px-3 py-3">
                                    <div className="flex items-center justify-between gap-3">
                                        <div className="text-sm font-medium text-white">{category.category}</div>
                                        <div className="text-sm text-[#A0A0A0]">{formatMoney(category.total)}</div>
                                    </div>
                                    <div className="mt-2 h-2 rounded-full bg-[#1E1E1E]">
                                        <div
                                            className="h-full rounded-full bg-[#4CBB17]"
                                            style={{ width: `${Math.min(Number(category.percent || 0), 100)}%` }}
                                        />
                                    </div>
                                    <div className="mt-2 text-xs text-[#7F7F7F]">
                                        {category.percent}% of total expense volume
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                <div className="rounded-2xl border border-[#242424] bg-[#111111] p-4">
                    <div className="flex items-center gap-2 text-sm font-semibold text-white">
                        <AlertTriangle className="h-4 w-4 text-[#FFB300]" />
                        Spend Alerts
                    </div>
                    <div className="mt-3 space-y-3">
                        {insightModel.alerts.length === 0 ? (
                            <div className="rounded-xl border border-[#1D1D1D] bg-[#0C0C0C] px-3 py-4 text-sm text-[#A0A0A0]">
                                No active spend alerts. Expense ratios and budgets look stable right now.
                            </div>
                        ) : (
                            insightModel.alerts.map((alert, index) => (
                                <div key={`${alert}-${index}`} className="rounded-xl border border-[#FFB30040] bg-[#FFB30012] px-3 py-3 text-sm text-[#F5DEB3]">
                                    {alert}
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
