import { useEffect, useState } from "react";
import {
    AlertTriangle,
    BarChart3,
    Download,
    Loader2,
    RefreshCw,
    TrendingDown,
    TrendingUp,
    Users,
    Wallet,
} from "lucide-react";
import {
    Bar,
    BarChart,
    CartesianGrid,
    Legend,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { useAuth, useUser } from "@clerk/clerk-react";
import { toast } from "sonner";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";

const PERIOD_OPTIONS = [
    { value: "monthly", label: "This Month" },
    { value: "quarterly", label: "This Quarter" },
    { value: "yearly", label: "This Year" },
];

function formatMoney(value) {
    return `₹${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function formatPercent(value) {
    return `${Number(value || 0).toFixed(1)}%`;
}

function ChartTooltip({ active, payload, label }) {
    if (!active || !payload?.length) {
        return null;
    }

    return (
        <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm shadow-lg">
            <div className="mb-1 text-xs text-[#A0A0A0]">{label}</div>
            {payload.map((entry) => (
                <div key={entry.dataKey} className="flex items-center justify-between gap-4">
                    <span style={{ color: entry.color }}>{entry.name}</span>
                    <span className="text-white">{typeof entry.value === "number" ? formatMoney(entry.value) : entry.value}</span>
                </div>
            ))}
        </div>
    );
}

function StatCard({ label, value, caption, icon: Icon, accent }) {
    return (
        <div className="mo-stat-card">
            <div className="mb-3 flex items-center justify-between">
                <span className="text-sm font-medium text-[#A0A0A0]">{label}</span>
                <Icon className="h-4 w-4" style={{ color: accent || "#A0A0A0" }} />
            </div>
            <div className="text-2xl font-bold text-white">{value}</div>
            <div className="mt-1 text-xs text-[#A0A0A0]">{caption}</div>
        </div>
    );
}

async function parseError(response, fallbackMessage) {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
        const payload = await response.json().catch(() => null);
        return payload?.message || payload?.error || fallbackMessage;
    }
    const text = await response.text().catch(() => "");
    return text || fallbackMessage;
}

export default function AnalyticsPage() {
    const { userId, orgId } = useOnboardingStatus();
    const { getToken } = useAuth();
    const { user } = useUser();

    const [period, setPeriod] = useState("monthly");
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [exporting, setExporting] = useState(false);

    useEffect(() => {
        if (user?.id && orgId) {
            fetchMetrics();
        }
    }, [user?.id, orgId, period]);

    async function buildHeaders() {
        const token = await getToken();
        return {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            "X-User-Id": userId || user?.id,
            "X-Org-Id": orgId,
        };
    }

    async function fetchMetrics() {
        try {
            setLoading(true);
            const headers = await buildHeaders();
            const response = await fetch(
                `/api/overview/metrics?orgId=${encodeURIComponent(orgId)}&period=${encodeURIComponent(period)}`,
                { headers }
            );

            if (!response.ok) {
                throw new Error(await parseError(response, "Failed to load overview metrics"));
            }

            const data = await response.json();
            setMetrics(data);
        } catch (error) {
            console.error("Failed to load overview metrics", error);
            toast.error(error.message || "Failed to load overview metrics");
            setMetrics(null);
        } finally {
            setLoading(false);
        }
    }

    async function handleExportReport() {
        try {
            setExporting(true);
            const headers = await buildHeaders();
            const response = await fetch(
                `/api/overview/export/pdf?orgId=${encodeURIComponent(orgId)}&period=${encodeURIComponent(period)}`,
                { headers }
            );

            if (!response.ok) {
                throw new Error(await parseError(response, "Failed to export overview report"));
            }

            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const disposition = response.headers.get("content-disposition");
            const filenameMatch = disposition?.match(/filename=\"([^\"]+)\"/);
            const filename = filenameMatch?.[1] || `overview-${period}-${new Date().toISOString().slice(0, 10)}.pdf`;

            const link = document.createElement("a");
            link.href = downloadUrl;
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(downloadUrl);
            toast.success("Overview report exported");
        } catch (error) {
            console.error("Failed to export overview report", error);
            toast.error(error.message || "Failed to export overview report");
        } finally {
            setExporting(false);
        }
    }

    if (loading) {
        return (
            <div className="flex h-96 items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
            </div>
        );
    }

    if (!metrics) {
        return (
            <div className="flex h-96 flex-col items-center justify-center gap-4">
                <AlertTriangle className="h-10 w-10 text-[#FFB300]" />
                <p className="text-[#A0A0A0]">Failed to load overview data</p>
                <button onClick={fetchMetrics} className="mo-btn-primary flex items-center gap-2">
                    <RefreshCw className="h-4 w-4" />
                    Retry
                </button>
            </div>
        );
    }

    const orgName = metrics.organization?.tradingName || metrics.organization?.legalName || "Your Business";
    const topClients = metrics.topClients || [];
    const monthComparisons = metrics.monthComparisons || [];
    const invoiceBreakdown = metrics.invoiceStatusBreakdown || {};
    const complianceSummary = metrics.complianceSummary || {};

    const monthChartData = monthComparisons.map((row) => ({
        label: row.label,
        Revenue: Number(row.revenue || 0),
        Expenses: Number(row.expenses || 0),
        Net: Number(row.netProfitLoss || 0),
    }));

    const topClientChartData = topClients.map((client) => ({
        label: client.clientName,
        Revenue: Number(client.revenue || 0),
    }));

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="mo-h1">Overview</h1>
                    <p className="mo-text-secondary mt-1">{metrics.reportTitle} for {orgName}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <select
                        value={period}
                        onChange={(event) => setPeriod(event.target.value)}
                        className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none"
                    >
                        {PERIOD_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                                {option.label}
                            </option>
                        ))}
                    </select>
                    <button onClick={fetchMetrics} className="mo-btn-secondary flex items-center gap-2" disabled={loading}>
                        <RefreshCw className="h-4 w-4" />
                        Refresh
                    </button>
                    <button
                        onClick={handleExportReport}
                        disabled={exporting}
                        className="mo-btn-primary flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-70"
                    >
                        {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                        {exporting ? "Generating..." : "Export Report"}
                    </button>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <StatCard
                    label="Total Revenue"
                    value={formatMoney(metrics.totalRevenue)}
                    caption={`${metrics.reportTitle}`}
                    icon={TrendingUp}
                    accent="#4CBB17"
                />
                <StatCard
                    label="Total Expenses"
                    value={formatMoney(metrics.totalExpenses)}
                    caption="Live expense transactions"
                    icon={TrendingDown}
                    accent="#CD1C18"
                />
                <StatCard
                    label="Net Profit/Loss"
                    value={formatMoney(metrics.netProfitLoss)}
                    caption={Number(metrics.netProfitLoss) >= 0 ? "Positive operating result" : "Operating loss for selected period"}
                    icon={Wallet}
                    accent={Number(metrics.netProfitLoss) >= 0 ? "#4CBB17" : "#CD1C18"}
                />
                <StatCard
                    label="Outstanding Invoices"
                    value={`${metrics.outstandingInvoicesCount}`}
                    caption={formatMoney(metrics.outstandingInvoicesAmount)}
                    icon={BarChart3}
                    accent="#FFB300"
                />
                <StatCard
                    label="Overdue Invoices"
                    value={`${metrics.overdueInvoicesCount}`}
                    caption={formatMoney(metrics.overdueInvoicesAmount)}
                    icon={AlertTriangle}
                    accent="#CD1C18"
                />
                <StatCard
                    label="New Clients"
                    value={`${metrics.newClients}`}
                    caption="Created in selected period"
                    icon={Users}
                    accent="#60A5FA"
                />
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
                <div className="mo-card">
                    <div className="mb-4">
                        <h2 className="mo-h2">Monthly Comparison</h2>
                        <p className="mo-text-secondary mt-1">Revenue, expenses, and net movement across the selected window.</p>
                    </div>
                    <div className="h-[340px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={monthChartData}>
                                <CartesianGrid stroke="#1F1F1F" vertical={false} />
                                <XAxis dataKey="label" stroke="#8F8F8F" tickLine={false} axisLine={false} />
                                <YAxis stroke="#8F8F8F" tickLine={false} axisLine={false} tickFormatter={(value) => `₹${Number(value).toLocaleString("en-IN")}`} />
                                <Tooltip content={<ChartTooltip />} />
                                <Legend />
                                <Bar dataKey="Revenue" fill="#4CBB17" radius={[6, 6, 0, 0]} />
                                <Bar dataKey="Expenses" fill="#CD1C18" radius={[6, 6, 0, 0]} />
                                <Bar dataKey="Net" fill="#60A5FA" radius={[6, 6, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="mo-card">
                    <div className="mb-4">
                        <h2 className="mo-h2">Invoice Status</h2>
                        <p className="mo-text-secondary mt-1">Breakdown of invoices issued in the selected period.</p>
                    </div>
                    <div className="grid gap-3">
                        <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] p-4">
                            <div className="text-xs uppercase tracking-wide text-[#A0A0A0]">Draft</div>
                            <div className="mt-1 text-2xl font-bold text-white">{invoiceBreakdown.draft || 0}</div>
                        </div>
                        <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] p-4">
                            <div className="text-xs uppercase tracking-wide text-[#A0A0A0]">Sent</div>
                            <div className="mt-1 text-2xl font-bold text-white">{invoiceBreakdown.sent || 0}</div>
                        </div>
                        <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] p-4">
                            <div className="text-xs uppercase tracking-wide text-[#A0A0A0]">Paid</div>
                            <div className="mt-1 text-2xl font-bold text-[#4CBB17]">{invoiceBreakdown.paid || 0}</div>
                        </div>
                        <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] p-4">
                            <div className="text-xs uppercase tracking-wide text-[#A0A0A0]">Overdue</div>
                            <div className="mt-1 text-2xl font-bold text-[#CD1C18]">{invoiceBreakdown.overdue || 0}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                <div className="mo-card">
                    <div className="mb-4">
                        <h2 className="mo-h2">Top Clients by Revenue</h2>
                        <p className="mo-text-secondary mt-1">Live ranking from income transactions matched to clients.</p>
                    </div>
                    {topClients.length === 0 ? (
                        <div className="rounded-xl border border-dashed border-[#2A2A2A] bg-[#111111] px-4 py-10 text-center text-sm text-[#A0A0A0]">
                            No client-linked income transactions in this period.
                        </div>
                    ) : (
                        <>
                            <div className="mb-5 h-[260px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={topClientChartData} layout="vertical" margin={{ left: 24 }}>
                                        <CartesianGrid stroke="#1F1F1F" horizontal={false} />
                                        <XAxis type="number" stroke="#8F8F8F" tickLine={false} axisLine={false} tickFormatter={(value) => `₹${Number(value).toLocaleString("en-IN")}`} />
                                        <YAxis type="category" dataKey="label" stroke="#8F8F8F" tickLine={false} axisLine={false} width={110} />
                                        <Tooltip content={<ChartTooltip />} />
                                        <Bar dataKey="Revenue" fill="#4CBB17" radius={[0, 6, 6, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                            <div className="overflow-hidden rounded-xl border border-[#202020]">
                                <table className="w-full text-sm">
                                    <thead className="bg-[#161616]">
                                        <tr>
                                            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">Client</th>
                                            <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">Revenue</th>
                                            <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">Transactions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-[#1F1F1F]">
                                        {topClients.map((client) => (
                                            <tr key={client.clientId || client.clientName} className="bg-[#101010]">
                                                <td className="px-4 py-3 text-white">{client.clientName}</td>
                                                <td className="px-4 py-3 text-right text-white">{formatMoney(client.revenue)}</td>
                                                <td className="px-4 py-3 text-right text-[#A0A0A0]">{client.transactionCount}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </div>

                <div className="mo-card">
                    <div className="mb-4">
                        <h2 className="mo-h2">Compliance Summary</h2>
                        <p className="mo-text-secondary mt-1">Regulatory readiness based on your live organization and invoice data.</p>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2">
                        <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] p-4">
                            <div className="text-xs uppercase tracking-wide text-[#A0A0A0]">Regulatory Completeness</div>
                            <div className="mt-1 text-2xl font-bold text-white">{formatPercent(complianceSummary.regulatoryCompletenessPercentage || 0)}</div>
                        </div>
                        <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] p-4">
                            <div className="text-xs uppercase tracking-wide text-[#A0A0A0]">GST Collected</div>
                            <div className="mt-1 text-2xl font-bold text-white">{formatMoney(complianceSummary.totalGstCollected)}</div>
                        </div>
                        <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] p-4">
                            <div className="text-xs uppercase tracking-wide text-[#A0A0A0]">Paid Invoices</div>
                            <div className="mt-1 text-2xl font-bold text-[#4CBB17]">{complianceSummary.paidInvoices || 0}</div>
                        </div>
                        <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] p-4">
                            <div className="text-xs uppercase tracking-wide text-[#A0A0A0]">Overdue Invoices</div>
                            <div className="mt-1 text-2xl font-bold text-[#CD1C18]">{complianceSummary.overdueInvoices || 0}</div>
                        </div>
                    </div>

                    <div className="mt-5 rounded-xl border border-[#2A2A2A] bg-[#111111] p-4">
                        <div className="mb-3 text-sm font-semibold text-white">Missing Compliance Fields</div>
                        {Array.isArray(complianceSummary.missingComplianceFields) && complianceSummary.missingComplianceFields.length > 0 ? (
                            <div className="space-y-2">
                                {complianceSummary.missingComplianceFields.map((item) => (
                                    <div key={item} className="rounded-lg border border-[#30261B] bg-[#FFB30010] px-3 py-2 text-sm text-[#D6B36A]">
                                        {item}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-sm text-[#A0A0A0]">No missing compliance fields detected.</div>
                        )}
                    </div>
                </div>
            </div>

            <div className="mo-card">
                <div className="mb-4">
                    <h2 className="mo-h2">Month-by-Month Comparison Table</h2>
                    <p className="mo-text-secondary mt-1">Revenue, expense, and net totals by month in the current reporting window.</p>
                </div>
                <div className="overflow-hidden rounded-xl border border-[#202020]">
                    <table className="w-full text-sm">
                        <thead className="bg-[#161616]">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">Month</th>
                                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">Revenue</th>
                                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">Expenses</th>
                                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">Net</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#1F1F1F]">
                            {monthComparisons.map((row) => (
                                <tr key={row.label} className="bg-[#101010]">
                                    <td className="px-4 py-3 text-white">{row.label}</td>
                                    <td className="px-4 py-3 text-right text-[#4CBB17]">{formatMoney(row.revenue)}</td>
                                    <td className="px-4 py-3 text-right text-[#CD1C18]">{formatMoney(row.expenses)}</td>
                                    <td className={`px-4 py-3 text-right font-medium ${Number(row.netProfitLoss) >= 0 ? "text-white" : "text-[#CD1C18]"}`}>
                                        {formatMoney(row.netProfitLoss)}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
