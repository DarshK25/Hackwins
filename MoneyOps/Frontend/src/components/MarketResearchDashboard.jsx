import { RefreshCw, TrendingUp, TrendingDown, AlertCircle } from "lucide-react";

const PRIORITY_BADGE = {
    high: "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]",
    medium: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
    low: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
};

function StatCard({ label, value, sub, iconColor, accent }) {
    return (
        <div className="mo-card">
            <p className="text-xs text-[#A0A0A0] font-medium uppercase tracking-wide mb-2">{label}</p>
            <p className="text-2xl font-bold" style={{ color: accent || "#ffffff" }}>{value}</p>
            {sub && <p className="text-xs text-[#A0A0A0] mt-1">{sub}</p>}
        </div>
    );
}

export function MarketResearchDashboard({ businessId, data, onRefresh }) {
    const mockData = {
        metrics: { revenueGrowth: 15, marketShare: 12, opportunityScore: 82, competitiveRank: "#3" },
        trends: [
            { category: "fintech_services", description: "Adoption of automated compliance tools", amount: 2500000, direction: "up", change: 35 },
            { category: "consulting", description: "Shift towards remote advisory", amount: 850000, direction: "up", change: 12 },
            { category: "legacy_software", description: "Declining interest in on-premise solutions", amount: 450000, direction: "down", change: 8 },
        ],
        insights: [
            { priority: "high", title: "Emerging Market Gap", message: "SME sector is underserved for automated GST filing in the western region.", action: "Review Strategy" },
            { priority: "medium", title: "Regulatory Change", message: "New tax compliance deadline extended by 30 days.", action: "View Details" },
            { priority: "medium", title: "Competitor Movement", message: "Competitor X has raised prices by 15%. Opportunity to capture share.", action: "Target New Clients" },
        ],
    };

    const activeData = data || mockData;
    const metrics = activeData.metrics || {};
    const trends = activeData.trends || [];
    const insights = activeData.insights || [];

    const formatIndustryName = (industry) =>
        industry.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" & ");

    return (
        <div className="flex flex-col gap-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-4">
                    <div className="rounded-xl p-3" style={{ backgroundColor: "#FFB30020", border: "1px solid #FFB30040" }}>
                        <TrendingUp className="h-6 w-6 text-[#FFB300]" />
                    </div>
                    <div>
                        <h1 className="mo-h1">Market Research Intelligence</h1>
                        <p className="mo-text-secondary mt-0.5">AI-powered market analysis & growth opportunities</p>
                    </div>
                </div>
                <button onClick={onRefresh} className="mo-btn-secondary flex items-center gap-2 text-sm">
                    <RefreshCw className="h-4 w-4" /> Refresh
                </button>
            </div>

            {/* Key Metrics */}
            <div className="grid gap-4 md:grid-cols-4">
                <StatCard label="Revenue Growth" value={`+${metrics.revenueGrowth || 0}%`} sub="vs last quarter" accent="#4CBB17" />
                <StatCard label="Market Share" value={`${metrics.marketShare || 0}%`} sub="Estimated" />
                <StatCard label="Growth Opportunity" value={`${metrics.opportunityScore || 0}/100`} sub="Potential score" accent="#60A5FA" />
                <StatCard label="Competitive Position" value={metrics.competitiveRank || "N/A"} sub="In your sector" />
            </div>

            {/* Transaction Trends */}
            <div className="mo-card">
                <h2 className="mo-h2 mb-1">Transaction Pattern Analysis</h2>
                <p className="mo-text-secondary mb-4">Market trends derived from your business transactions</p>
                <div className="flex flex-col gap-3">
                    {trends.map((trend, i) => (
                        <div key={i} className="flex items-center justify-between p-3 rounded-xl border border-[#2A2A2A] hover:border-[#3A3A3A] transition-all">
                            <div className="flex items-center gap-3">
                                <div className="h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: trend.direction === "up" ? "#4CBB17" : "#CD1C18" }} />
                                <div>
                                    <p className="font-semibold text-white text-sm">{formatIndustryName(trend.category)}</p>
                                    <p className="text-xs text-[#A0A0A0]">{trend.description}</p>
                                </div>
                            </div>
                            <div className="text-right flex-shrink-0">
                                <p className="font-semibold text-white text-sm">₹{trend.amount.toLocaleString()}</p>
                                <div className={`text-xs flex items-center justify-end gap-1 ${trend.direction === "up" ? "text-[#4CBB17]" : "text-[#CD1C18]"}`}>
                                    {trend.direction === "up" ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                                    {trend.change}%
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* AI Insights */}
            <div className="mo-card">
                <h2 className="mo-h2 mb-1">AI Market Insights & Recommendations</h2>
                <p className="mo-text-secondary mb-4">AI-powered analysis of your market position</p>
                <div className="flex flex-col gap-3">
                    {insights.map((insight, i) => (
                        <div key={i} className="p-4 rounded-xl border transition-all" style={{
                            backgroundColor: insight.priority === "high" ? "#CD1C1810" : insight.priority === "medium" ? "#FFB30010" : "#4CBB1710",
                            borderColor: insight.priority === "high" ? "#CD1C1840" : insight.priority === "medium" ? "#FFB30040" : "#4CBB1740",
                        }}>
                            <div className="flex items-start gap-3">
                                {insight.priority === "high" && <AlertCircle className="h-4 w-4 text-[#CD1C18] mt-0.5 flex-shrink-0" />}
                                <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                                        <span className={`text-xs px-2 py-0.5 rounded-md font-medium border ${PRIORITY_BADGE[insight.priority] || PRIORITY_BADGE.low}`}>{insight.priority}</span>
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
