import { RefreshCw, TrendingUp, TrendingDown, AlertTriangle, Users, DollarSign, Activity } from "lucide-react";

const PRIORITY_BADGE = {
    high: "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]",
    medium: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
    low: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
};

function StatCard({ label, value, sub, icon: Icon, iconColor }) {
    return (
        <div className="mo-card">
            <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-[#A0A0A0] font-medium uppercase tracking-wide">{label}</p>
                {Icon && <Icon className="h-4 w-4" style={{ color: iconColor || "#A0A0A0" }} />}
            </div>
            <p className="text-2xl font-bold text-white">{value}</p>
            {sub && <p className="text-xs text-[#A0A0A0] mt-1">{sub}</p>}
        </div>
    );
}

export function SalesCRMDashboard({ businessId, data, onRefresh }) {
    const mockData = {
        metrics: { totalClients: 145, activeClients: 82, atRiskClients: 12, avgClientValue: 54000, healthScore: 78, paymentReliability: 85, engagementRate: 62, retentionRate: 91 },
        clients: [
            { name: "TechFlow Solutions", invoiceCount: 24, totalRevenue: 1250000, growth: 18, trend: "up" },
            { name: "Acme Corp", invoiceCount: 15, totalRevenue: 850000, growth: 5, trend: "down" },
            { name: "Globex Inc", invoiceCount: 12, totalRevenue: 620000, growth: 12, trend: "up" },
            { name: "Soylent Corp", invoiceCount: 8, totalRevenue: 450000, growth: 2, trend: "down" },
            { name: "Initech", invoiceCount: 6, totalRevenue: 320000, growth: 8, trend: "up" },
        ],
        insights: [
            { priority: "high", title: "Churn Risk Alert", message: "Acme Corp shows a 15% drop in engagement over the last 30 days.", action: "Schedule Review" },
            { priority: "medium", title: "Upsell Opportunity", message: "TechFlow Solutions usage has increased by 20%. Consider pitching the Enterprise plan.", action: "Send Proposal" },
            { priority: "low", title: "Contract Renewal", message: "Globex Inc contract expires in 45 days.", action: "Prepare Renewal" },
        ],
    };

    const activeData = data || mockData;
    const metrics = activeData.metrics || {};
    const clients = activeData.clients || [];
    const insights = activeData.insights || [];

    return (
        <div className="flex flex-col gap-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-4">
                    <div className="rounded-xl p-3" style={{ backgroundColor: "#4CBB1720", border: "1px solid #4CBB1740" }}>
                        <Users className="h-6 w-6 text-[#4CBB17]" />
                    </div>
                    <div>
                        <h1 className="mo-h1">Sales & CRM Intelligence</h1>
                        <p className="mo-text-secondary mt-0.5">AI-powered client relationship management</p>
                    </div>
                </div>
                <button onClick={onRefresh} className="mo-btn-secondary flex items-center gap-2 text-sm">
                    <RefreshCw className="h-4 w-4" /> Refresh
                </button>
            </div>

            {/* Key Metrics */}
            <div className="grid gap-4 md:grid-cols-4">
                <StatCard label="Total Clients" value={metrics.totalClients || 0} sub="All time" icon={Users} iconColor="#A0A0A0" />
                <StatCard label="Active Clients" value={metrics.activeClients || 0} sub="Last 90 days" icon={Activity} iconColor="#4CBB17" />
                <StatCard label="At-Risk Clients" value={metrics.atRiskClients || 0} sub="No activity 90+ days" icon={AlertTriangle} iconColor="#CD1C18" />
                <StatCard label="Avg Client Value" value={`₹${(metrics.avgClientValue || 0).toLocaleString()}`} sub="Lifetime value" icon={DollarSign} iconColor="#FFB300" />
            </div>

            {/* Client Health */}
            <div className="mo-card">
                <h2 className="mo-h2 mb-4">Client Relationship Health</h2>
                <div className="flex items-center justify-between mb-3">
                    <span className="text-sm text-[#A0A0A0]">Overall Health Score</span>
                    <span className="text-2xl font-bold text-[#4CBB17]">{metrics.healthScore || 0}/100</span>
                </div>
                <div className="h-2 w-full rounded-full bg-[#2A2A2A] mb-5">
                    <div className="h-full rounded-full transition-all" style={{ width: `${metrics.healthScore || 0}%`, backgroundColor: "#4CBB17" }} />
                </div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                    {[
                        { label: "Payment Reliability", value: `${metrics.paymentReliability || 0}%` },
                        { label: "Engagement Rate", value: `${metrics.engagementRate || 0}%` },
                        { label: "Retention Rate", value: `${metrics.retentionRate || 0}%` },
                    ].map(({ label, value }) => (
                        <div key={label}>
                            <p className="text-xs text-[#A0A0A0] mb-1">{label}</p>
                            <p className="font-semibold text-white">{value}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Top Clients */}
            <div className="mo-card">
                <h2 className="mo-h2 mb-4">Top Clients by Revenue</h2>
                <div className="flex flex-col gap-3">
                    {clients.slice(0, 5).map((client, i) => (
                        <div key={i} className="flex items-center justify-between p-3 rounded-xl border border-[#2A2A2A] hover:border-[#3A3A3A] transition-all">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-black flex-shrink-0" style={{ backgroundColor: "#4CBB17" }}>
                                    {i + 1}
                                </div>
                                <div>
                                    <p className="font-semibold text-white text-sm">{client.name}</p>
                                    <p className="text-xs text-[#A0A0A0]">{client.invoiceCount} invoices</p>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="font-semibold text-white text-sm">₹{client.totalRevenue.toLocaleString()}</p>
                                <div className={`text-xs flex items-center justify-end gap-1 ${client.trend === "up" ? "text-[#4CBB17]" : "text-[#CD1C18]"}`}>
                                    {client.trend === "up"
                                        ? <TrendingUp className="h-3 w-3" />
                                        : <TrendingDown className="h-3 w-3" />}
                                    {client.growth}%
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* AI Insights */}
            <div className="mo-card">
                <h2 className="mo-h2 mb-1">AI Insights & Recommendations</h2>
                <p className="mo-text-secondary mb-4">AI-powered client intelligence</p>
                <div className="flex flex-col gap-3">
                    {insights.map((insight, i) => (
                        <div key={i} className="p-4 rounded-xl border transition-all" style={{
                            backgroundColor: insight.priority === "high" ? "#CD1C1810" : insight.priority === "medium" ? "#FFB30010" : "#4CBB1710",
                            borderColor: insight.priority === "high" ? "#CD1C1840" : insight.priority === "medium" ? "#FFB30040" : "#4CBB1740",
                        }}>
                            <div className="flex items-start gap-3">
                                {insight.priority === "high" && <AlertTriangle className="h-4 w-4 text-[#CD1C18] mt-0.5 flex-shrink-0" />}
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                                        <span className={`text-xs px-2 py-0.5 rounded-md font-medium border ${PRIORITY_BADGE[insight.priority]}`}>{insight.priority}</span>
                                        <span className="font-semibold text-white text-sm">{insight.title}</span>
                                    </div>
                                    <p className="text-sm text-[#A0A0A0]">{insight.message}</p>
                                    {insight.action && (
                                        <button className="mt-2 text-xs text-[#4CBB17] hover:underline font-medium">{insight.action} →</button>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
