import { Calculator, TrendingUp, AlertCircle, CheckCircle } from "lucide-react";

const accounts = [
    { id: 1, name: "Business Checking", bank: "Chase", balance: 45231.89, type: "checking" },
    { id: 2, name: "Savings Account", bank: "Wells Fargo", balance: 125000.0, type: "savings" },
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
    { value: "₹16,76,880", label: "Total Assets", color: "#4CBB17" },
    { value: "₹25,430", label: "Total Liabilities", color: "#CD1C18" },
    { value: "₹16,51,450", label: "Net Worth", color: "#ffffff" },
    { value: "+12.5%", label: "Monthly Growth", color: "#4CBB17" },
];

export default function FinancesPage() {
    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Finances</h1>
                    <p className="mo-text-secondary mt-1">
                        Manage your accounts, transactions, and financial data
                    </p>
                </div>
                <div className="flex gap-2">
                    <button className="mo-btn-secondary flex items-center gap-2">
                        <Calculator className="h-4 w-4" /> Reconcile Accounts
                    </button>
                    <button className="mo-btn-primary flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" /> Generate Report
                    </button>
                </div>
            </div>

            {/* ── Account Cards ─────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-3">
                {accounts.map((account) => (
                    <div key={account.id} className="mo-stat-card">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-sm font-medium text-white">{account.name}</span>
                            <span
                                className={`text-xs px-2 py-0.5 rounded-md font-medium border ${account.type === "credit"
                                        ? "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]"
                                        : "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]"
                                    }`}
                            >
                                {account.type}
                            </span>
                        </div>
                        <div
                            className="text-2xl font-bold"
                            style={{ color: account.balance < 0 ? "#CD1C18" : "#ffffff" }}
                        >
                            ₹{Math.abs(account.balance).toLocaleString("en-IN")}
                            {account.balance < 0 && (
                                <span className="text-sm font-normal text-[#A0A0A0] ml-1">(owed)</span>
                            )}
                        </div>
                        <p className="text-xs text-[#A0A0A0] mt-1">{account.bank}</p>
                    </div>
                ))}
            </div>

            {/* ── Agent Status + Quick Actions ──────────────────────────────── */}
            <div className="grid gap-6 md:grid-cols-2">
                {/* Finance Agent Status */}
                <div className="mo-card">
                    <h2 className="mo-h2 mb-1">Finance Agent Status</h2>
                    <p className="mo-text-secondary mb-4">Current automated finance operations</p>
                    <div className="space-y-3">
                        {recentActivity.map((activity) => (
                            <div key={activity.id} className="flex items-center gap-3 p-3 bg-[#111111] rounded-lg border border-[#2A2A2A]">
                                <div className="flex-shrink-0">
                                    {activity.status === "success" ? (
                                        <CheckCircle className="h-5 w-5 text-[#4CBB17]" />
                                    ) : (
                                        <AlertCircle className="h-5 w-5 text-[#FFB300]" />
                                    )}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-white">{activity.description}</p>
                                    <p className="text-xs text-[#A0A0A0] mt-0.5">{activity.time}</p>
                                </div>
                                <span
                                    className={`text-xs px-2 py-0.5 rounded-md font-medium flex-shrink-0 border ${activity.status === "success"
                                            ? "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]"
                                            : "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]"
                                        }`}
                                >
                                    {activity.status}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Quick Actions */}
                <div className="mo-card">
                    <h2 className="mo-h2 mb-1">Quick Actions</h2>
                    <p className="mo-text-secondary mb-4">Common finance management tasks</p>
                    <div className="space-y-2">
                        {quickActions.map(({ label, icon: Icon }) => (
                            <button
                                key={label}
                                className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-[#A0A0A0] border border-[#2A2A2A] bg-[#111111] hover:border-[#4CBB17] hover:text-white transition-all"
                            >
                                <Icon className="h-4 w-4 text-[#4CBB17]" />
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* ── Financial Summary ──────────────────────────────────────────── */}
            <div className="mo-card">
                <h2 className="mo-h2 mb-1">Financial Summary</h2>
                <p className="mo-text-secondary mb-6">Overview of your financial position</p>
                <div className="grid gap-6 md:grid-cols-4">
                    {summaryStats.map(({ value, label, color }) => (
                        <div key={label} className="text-center p-4 bg-[#111111] rounded-xl border border-[#2A2A2A]">
                            <div className="text-2xl font-bold" style={{ color }}>{value}</div>
                            <div className="text-sm text-[#A0A0A0] mt-1">{label}</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
