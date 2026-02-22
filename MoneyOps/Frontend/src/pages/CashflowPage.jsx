import { TrendingUp, TrendingDown, AlertTriangle, Calendar } from "lucide-react";

const forecastData = [
    { period: "Next 7 days", inflow: 15000, outflow: 12000, net: 3000, status: "positive" },
    { period: "Next 30 days", inflow: 65000, outflow: 48000, net: 17000, status: "positive" },
    { period: "Next 90 days", inflow: 195000, outflow: 165000, net: 30000, status: "positive" },
];

const upcomingPayments = [
    { id: 1, description: "Office Rent", amount: 3500, dueDate: "2024-01-25", priority: "high" },
    { id: 2, description: "Software Subscriptions", amount: 890, dueDate: "2024-01-28", priority: "medium" },
    { id: 3, description: "Vendor Payment - Acme Corp", amount: 12500, dueDate: "2024-02-01", priority: "high" },
    { id: 4, description: "Utilities", amount: 450, dueDate: "2024-02-05", priority: "low" },
];

const expectedIncome = [
    { id: 1, description: "Client A - Project Payment", amount: 25000, expectedDate: "2024-01-30" },
    { id: 2, description: "Client B - Monthly Retainer", amount: 8000, expectedDate: "2024-02-01" },
    { id: 3, description: "Client C - Invoice #1234", amount: 15000, expectedDate: "2024-02-15" },
];

const insights = [
    {
        border: "#4CBB1740",
        bg: "#4CBB1710",
        title: "Positive Trend",
        titleColor: "#4CBB17",
        body: "Your cashflow is trending positively with a 15% increase over the last quarter.",
    },
    {
        border: "#FFB30040",
        bg: "#FFB30010",
        title: "Optimization Opportunity",
        titleColor: "#FFB300",
        body: "Consider negotiating extended payment terms with vendors to improve cashflow timing.",
    },
    {
        border: "#60A5FA40",
        bg: "#60A5FA10",
        title: "Recommendation",
        titleColor: "#60A5FA",
        body: "Set up automatic invoice reminders to reduce payment delays by an estimated 8 days.",
    },
];

const PRIORITY_BADGE = {
    high: "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]",
    medium: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
    low: "bg-[#A0A0A020] text-[#A0A0A0] border-[#A0A0A040]",
};

export default function CashflowPage() {
    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Cash Flow</h1>
                    <p className="mo-text-secondary mt-1">Monitor and forecast your business cashflow</p>
                </div>
                <div className="flex gap-2">
                    <button className="mo-btn-secondary flex items-center gap-2">
                        <Calendar className="h-4 w-4" /> Schedule Payments
                    </button>
                    <button className="mo-btn-primary flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" /> Generate Forecast
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
                                <span className="font-medium text-[#4CBB17]">₹{forecast.inflow.toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-[#A0A0A0]">Outflow</span>
                                <span className="font-medium text-[#CD1C18]">₹{forecast.outflow.toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between text-base font-bold border-t border-[#2A2A2A] pt-3 mt-1">
                                <span className="text-white">Net</span>
                                <span style={{ color: forecast.net >= 0 ? "#4CBB17" : "#CD1C18" }}>
                                    ₹{forecast.net.toLocaleString()}
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
                        {upcomingPayments.map((payment) => (
                            <div
                                key={payment.id}
                                className="flex items-center justify-between p-3 rounded-xl border border-[#2A2A2A] bg-[#111111] hover:border-[#3A3A3A] transition-colors"
                            >
                                <div className="flex-1 min-w-0 mr-3">
                                    <p className="font-medium text-white text-sm truncate">{payment.description}</p>
                                    <p className="text-xs text-[#A0A0A0] mt-0.5">Due: {payment.dueDate}</p>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                    <span className={`text-xs px-2 py-0.5 rounded-md font-medium border ${PRIORITY_BADGE[payment.priority]}`}>
                                        {payment.priority}
                                    </span>
                                    <span className="font-bold text-[#CD1C18] text-sm">
                                        ₹{payment.amount.toLocaleString()}
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
                        {expectedIncome.map((income) => (
                            <div
                                key={income.id}
                                className="flex items-center justify-between p-3 rounded-xl border border-[#2A2A2A] bg-[#111111] hover:border-[#3A3A3A] transition-colors"
                            >
                                <div className="flex-1 min-w-0 mr-3">
                                    <p className="font-medium text-white text-sm truncate">{income.description}</p>
                                    <p className="text-xs text-[#A0A0A0] mt-0.5">Expected: {income.expectedDate}</p>
                                </div>
                                <span className="font-bold text-[#4CBB17] text-sm flex-shrink-0">
                                    ₹{income.amount.toLocaleString()}
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
                        <p className="mo-text-secondary">AI-powered cashflow analysis and recommendations</p>
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
