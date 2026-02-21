import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, AlertTriangle, Calendar } from "lucide-react";

// ── Static data ───────────────────────────────────────────────────────────────

const forecastData = [
    {
        period: "Next 7 days",
        inflow: 15000,
        outflow: 12000,
        net: 3000,
        status: "positive",
    },
    {
        period: "Next 30 days",
        inflow: 65000,
        outflow: 48000,
        net: 17000,
        status: "positive",
    },
    {
        period: "Next 90 days",
        inflow: 195000,
        outflow: 165000,
        net: 30000,
        status: "positive",
    },
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

const insightCards = [
    {
        color: "green",
        title: "Positive Trend",
        body: "Your cashflow is trending positively with a 15% increase over the last quarter.",
    },
    {
        color: "yellow",
        title: "Optimization Opportunity",
        body: "Consider negotiating extended payment terms with vendors to improve cashflow timing.",
    },
    {
        color: "blue",
        title: "Recommendation",
        body: "Set up automatic invoice reminders to reduce payment delays by an estimated 8 days.",
    },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Maps priority string → Badge variant */
const getPriorityVariant = (priority) => {
    switch (priority) {
        case "high": return "destructive";
        case "medium": return "default";
        case "low": return "secondary";
        default: return "default";
    }
};

/** Tailwind classes for the insight color band */
const insightColorClasses = {
    green: { wrapper: "bg-green-50 border-green-200", heading: "text-green-800", body: "text-green-700" },
    yellow: { wrapper: "bg-yellow-50 border-yellow-200", heading: "text-yellow-800", body: "text-yellow-700" },
    blue: { wrapper: "bg-blue-50 border-blue-200", heading: "text-blue-800", body: "text-blue-700" },
};

// ── Page ─────────────────────────────────────────────────────────────────────

export default function CashflowPage() {
    return (
        <div className="flex flex-col gap-6">

            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Cashflow Management</h1>
                    <p className="text-slate-500 text-sm mt-1">
                        Monitor and forecast your business cashflow
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline">
                        <Calendar className="mr-2 h-4 w-4" />
                        Schedule Payments
                    </Button>
                    <Button>
                        <TrendingUp className="mr-2 h-4 w-4" />
                        Generate Forecast
                    </Button>
                </div>
            </div>

            {/* ── Forecast Cards ─────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-3">
                {forecastData.map((forecast, index) => (
                    <Card key={index}>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">{forecast.period}</CardTitle>
                            <Badge variant={forecast.status === "positive" ? "success" : "destructive"}>
                                {forecast.status}
                            </Badge>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span className="text-green-600">Inflow</span>
                                    <span className="font-medium">₹{forecast.inflow.toLocaleString()}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-red-600">Outflow</span>
                                    <span className="font-medium">₹{forecast.outflow.toLocaleString()}</span>
                                </div>
                                <div className="flex justify-between text-lg font-bold border-t pt-2 mt-2">
                                    <span>Net</span>
                                    <span className={forecast.net >= 0 ? "text-green-600" : "text-red-600"}>
                                        ₹{forecast.net.toLocaleString()}
                                    </span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* ── Payments & Income ──────────────────────────────────────────── */}
            <div className="grid gap-6 md:grid-cols-2">

                {/* Upcoming Payments */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingDown className="h-5 w-5 text-red-500" />
                            Upcoming Payments
                        </CardTitle>
                        <CardDescription>Scheduled outgoing payments</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {upcomingPayments.map((payment) => (
                            <div
                                key={payment.id}
                                className="flex items-center justify-between p-3 border border-slate-100 rounded-lg hover:bg-slate-50 transition-colors"
                            >
                                <div className="flex-1 min-w-0 mr-3">
                                    <p className="font-medium truncate">{payment.description}</p>
                                    <p className="text-xs text-slate-400 mt-0.5">Due: {payment.dueDate}</p>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                    <Badge variant={getPriorityVariant(payment.priority)}>
                                        {payment.priority}
                                    </Badge>
                                    <span className="font-bold text-red-600 text-sm">
                                        ₹{payment.amount.toLocaleString()}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </CardContent>
                </Card>

                {/* Expected Income */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="h-5 w-5 text-green-500" />
                            Expected Income
                        </CardTitle>
                        <CardDescription>Anticipated incoming payments</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {expectedIncome.map((income) => (
                            <div
                                key={income.id}
                                className="flex items-center justify-between p-3 border border-slate-100 rounded-lg hover:bg-slate-50 transition-colors"
                            >
                                <div className="flex-1 min-w-0 mr-3">
                                    <p className="font-medium truncate">{income.description}</p>
                                    <p className="text-xs text-slate-400 mt-0.5">
                                        Expected: {income.expectedDate}
                                    </p>
                                </div>
                                <span className="font-bold text-green-600 text-sm flex-shrink-0">
                                    ₹{income.amount.toLocaleString()}
                                </span>
                            </div>
                        ))}
                    </CardContent>
                </Card>
            </div>

            {/* ── AI Insights ────────────────────────────────────────────────── */}
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5 text-yellow-500" />
                        Cashflow Insights
                    </CardTitle>
                    <CardDescription>
                        AI-powered cashflow analysis and recommendations
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {insightCards.map(({ color, title, body }) => {
                        const cls = insightColorClasses[color];
                        return (
                            <div
                                key={title}
                                className={`p-4 border rounded-lg ${cls.wrapper}`}
                            >
                                <h4 className={`font-medium mb-1 ${cls.heading}`}>{title}</h4>
                                <p className={`text-sm ${cls.body}`}>{body}</p>
                            </div>
                        );
                    })}
                </CardContent>
            </Card>
        </div>
    );
}
