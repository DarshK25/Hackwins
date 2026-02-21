import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calculator, TrendingUp, AlertCircle, CheckCircle } from "lucide-react";

// ── Static data ───────────────────────────────────────────────────────────────

const accounts = [
    { id: 1, name: "Business Checking", bank: "Chase", balance: 45231.89, type: "checking" },
    { id: 2, name: "Savings Account", bank: "Wells Fargo", balance: 125000.00, type: "savings" },
    { id: 3, name: "Business Credit", bank: "American Express", balance: -2543.21, type: "credit" },
];

const recentActivity = [
    { id: 1, description: "Automatic categorization completed", status: "success", time: "2 minutes ago" },
    { id: 2, description: "Account reconciliation in progress", status: "pending", time: "5 minutes ago" },
    { id: 3, description: "Monthly financial report generated", status: "success", time: "1 hour ago" },
];

const quickActions = [
    { label: "Categorize Transactions", icon: Calculator },
    { label: "Reconcile Accounts", icon: TrendingUp },
    { label: "Review Anomalies", icon: AlertCircle },
    { label: "Generate Financial Report", icon: CheckCircle },
];

const summaryStats = [
    { value: "₹16,76,880", label: "Total Assets", color: "text-green-600" },
    { value: "₹25,430", label: "Total Liabilities", color: "text-red-600" },
    { value: "₹16,51,450", label: "Net Worth", color: "text-blue-600" },
    { value: "+12.5%", label: "Monthly Growth", color: "text-purple-600" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Returns the Badge variant based on account type */
const getAccountVariant = (type) =>
    type === "credit" ? "destructive" : "default";

// ── Page ─────────────────────────────────────────────────────────────────────

export default function FinancesPage() {
    return (
        <div className="flex flex-col gap-6">

            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Finances</h1>
                    <p className="text-slate-500 text-sm mt-1">
                        Manage your accounts, transactions, and financial data
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline">
                        <Calculator className="mr-2 h-4 w-4" />
                        Reconcile Accounts
                    </Button>
                    <Button>
                        <TrendingUp className="mr-2 h-4 w-4" />
                        Generate Report
                    </Button>
                </div>
            </div>

            {/* ── Account Cards ──────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-3">
                {accounts.map((account) => (
                    <Card key={account.id}>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle className="text-sm font-medium">{account.name}</CardTitle>
                            <Badge variant={getAccountVariant(account.type)}>
                                {account.type}
                            </Badge>
                        </CardHeader>
                        <CardContent>
                            <div className={`text-2xl font-bold ${account.balance < 0 ? "text-red-600" : ""}`}>
                                ₹{Math.abs(account.balance).toLocaleString("en-IN")}
                                {account.balance < 0 && (
                                    <span className="text-sm font-normal text-slate-400 ml-1">(owed)</span>
                                )}
                            </div>
                            <p className="text-xs text-slate-400 mt-0.5">{account.bank}</p>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* ── Agent Status + Quick Actions ───────────────────────────────── */}
            <div className="grid gap-6 md:grid-cols-2">

                {/* Finance Agent Status */}
                <Card>
                    <CardHeader>
                        <CardTitle>Finance Agent Status</CardTitle>
                        <CardDescription>Current automated finance operations</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {recentActivity.map((activity) => (
                            <div key={activity.id} className="flex items-center gap-3">
                                <div className="flex-shrink-0">
                                    {activity.status === "success" ? (
                                        <CheckCircle className="h-5 w-5 text-green-500" />
                                    ) : (
                                        <AlertCircle className="h-5 w-5 text-yellow-500" />
                                    )}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium">{activity.description}</p>
                                    <p className="text-xs text-slate-400 mt-0.5">{activity.time}</p>
                                </div>
                                <Badge
                                    variant={activity.status === "success" ? "success" : "warning"}
                                    className="flex-shrink-0"
                                >
                                    {activity.status}
                                </Badge>
                            </div>
                        ))}
                    </CardContent>
                </Card>

                {/* Quick Actions */}
                <Card>
                    <CardHeader>
                        <CardTitle>Quick Actions</CardTitle>
                        <CardDescription>Common finance management tasks</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {quickActions.map(({ label, icon: Icon }) => (
                            <Button
                                key={label}
                                className="w-full justify-start"
                                variant="outline"
                            >
                                <Icon className="mr-2 h-4 w-4" />
                                {label}
                            </Button>
                        ))}
                    </CardContent>
                </Card>
            </div>

            {/* ── Financial Summary ──────────────────────────────────────────── */}
            <Card>
                <CardHeader>
                    <CardTitle>Financial Summary</CardTitle>
                    <CardDescription>Overview of your financial position</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="grid gap-6 md:grid-cols-4">
                        {summaryStats.map(({ value, label, color }) => (
                            <div key={label} className="text-center">
                                <div className={`text-2xl font-bold ${color}`}>{value}</div>
                                <div className="text-sm text-slate-500 mt-1">{label}</div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
