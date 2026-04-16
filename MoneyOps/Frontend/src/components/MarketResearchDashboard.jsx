import { RefreshCw, TrendingUp, TrendingDown, AlertCircle, Wifi, WifiOff } from "lucide-react";

const PRIORITY_BADGE = {
    high: "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]",
    medium: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
    low: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
};

function StatCard({ label, value, sub, accent }) {
    return (
        <div className="mo-card">
            <p className="text-xs text-[#A0A0A0] font-medium uppercase tracking-wide mb-2">{label}</p>
            <p className="text-2xl font-bold" style={{ color: accent || "#ffffff" }}>{value}</p>
            {sub && <p className="text-xs text-[#A0A0A0] mt-1">{sub}</p>}
        </div>
    );
}

function deriveMetrics(snapshot) {
    if (!snapshot) return { revenueGrowth: 0, marketShare: 0, opportunityScore: 0, competitiveRank: "N/A" };
    const clientCount = snapshot?.client_count || snapshot?.totalClients || snapshot?.active_clients || snapshot?.total_clients || 0;
    const overdueCount = snapshot?.overdue_count || snapshot?.overdueCount || 0;
    const margin = snapshot.profit_margin || 0;
    const opportunityScore = Math.min(100, Math.max(0, Math.round(
        (margin > 50 ? 80 : margin > 30 ? 65 : margin > 10 ? 50 : 35)
        + (clientCount > 5 ? 10 : 5)
        + (overdueCount === 0 ? 10 : overdueCount < 3 ? 5 : 0)
    )));
    const revenueGrowth = margin > 60 ? 18 : margin > 40 ? 12 : margin > 20 ? 7 : 3;
    const marketShare = clientCount > 10 ? 18 : clientCount > 5 ? 12 : 6;
    const competitiveRank = opportunityScore > 75 ? "#2" : opportunityScore > 55 ? "#3" : "#5";
    return { revenueGrowth, marketShare, opportunityScore, competitiveRank };
}

function deriveTrends(snapshot, marketData) {
    const trends = [];
    const revenue = snapshot?.revenue || 0;

    // From actual invoice/client data
    if (snapshot?.paid_count > 0) {
        trends.push({
            category: "professional_services",
            description: `${snapshot.paid_count} invoices paid, ${snapshot.pending_count} pending`,
            amount: Math.round(revenue * 0.6),
            direction: "up",
            change: Math.round(snapshot.profit_margin || 10),
        });
    }
    if (snapshot?.overdue_count > 0) {
        trends.push({
            category: "overdue_recovery",
            description: `₹${snapshot.overdue_amount?.toLocaleString('en-IN')} at risk — immediate follow-up needed`,
            amount: Math.round(snapshot.overdue_amount || 0),
            direction: "down",
            change: Math.round((snapshot.overdue_amount / (revenue || 1)) * 100),
        });
    }
    if (snapshot?.total_clients > 0) {
        trends.push({
            category: "client_expansion",
            description: `${snapshot.total_clients} active clients — ${snapshot.total_clients < 5 ? "scale up client acquisition" : "healthy client base"}`,
            amount: Math.round(revenue / (snapshot.total_clients || 1)),
            direction: snapshot.total_clients >= 5 ? "up" : "down",
            change: snapshot.total_clients >= 5 ? 15 : 5,
        });
    }

    // From Tavily news — extract top headlines as trend signals
    const news = marketData?.news?.news || [];
    if (news.length > 0) {
        trends.push({
            category: "live_market_signal",
            description: news[0]?.split("(")[0]?.trim() || "Market intelligence updated",
            amount: 0,
            direction: "up",
            change: null,
            isLive: true,
        });
    }

    return trends;
}

function deriveInsights(snapshot, marketData) {
    const insights = [];
    const newsAnswer = marketData?.news?.answer || "";
    const competitorAnswer = marketData?.competitors?.competitors_answer || "";
    const competitorMoves = marketData?.competitors?.recent_moves || "";
    const opportunitiesAnswer = marketData?.opportunities?.opportunities || "";

    // Critical: overdue invoices
    if (snapshot?.overdue_count > 0) {
        insights.push({
            priority: "high",
            title: "Cash Flow Risk",
            message: `You have ${snapshot.overdue_count} overdue invoice${snapshot.overdue_count > 1 ? "s" : ""} totaling ₹${snapshot.overdue_amount?.toLocaleString('en-IN')}. Follow up immediately to protect your ₹${snapshot.net_profit?.toLocaleString('en-IN')} net profit.`,
            action: "View Overdue Invoices",
            link: "/invoices?filter=overdue",
        });
    }

    // Live competitor intelligence from Tavily
    if (competitorMoves && competitorMoves.length > 50) {
        insights.push({
            priority: "medium",
            title: "Competitor Movement Detected",
            message: competitorMoves.slice(0, 180) + (competitorMoves.length > 180 ? "..." : ""),
            action: "Analyze Competitors",
        });
    } else if (competitorAnswer && competitorAnswer.length > 50) {
        insights.push({
            priority: "medium",
            title: "Competitive Landscape",
            message: competitorAnswer.slice(0, 180) + (competitorAnswer.length > 180 ? "..." : ""),
            action: "View Details",
        });
    }

    // Live growth opportunity from Tavily
    if (opportunitiesAnswer && opportunitiesAnswer.length > 50) {
        insights.push({
            priority: "low",
            title: "Growth Opportunity",
            message: opportunitiesAnswer.slice(0, 200) + (opportunitiesAnswer.length > 200 ? "..." : ""),
            action: "Explore Opportunity",
        });
    }

    // Live news signal
    if (newsAnswer && newsAnswer.length > 50) {
        insights.push({
            priority: "medium",
            title: "Market Intelligence",
            message: newsAnswer.slice(0, 200) + (newsAnswer.length > 200 ? "..." : ""),
            action: "View Full Report",
        });
    }

    // Positive signal: strong margin
    if ((snapshot?.profit_margin || 0) > 50) {
        insights.push({
            priority: "low",
            title: "Strong Profitability Signal",
            message: `Your ${snapshot.profit_margin}% profit margin is significantly above industry average. This is the right time to reinvest in client acquisition or service expansion.`,
            action: "Plan Expansion",
        });
    }

    // Fallback if no real data yet
    if (insights.length === 0) {
        insights.push({
            priority: "medium",
            title: "Market Analysis Loading",
            message: "Live market intelligence is being gathered. Ask the voice agent 'What are my growth opportunities?' to trigger analysis.",
            action: null,
        });
    }

    return insights;
}

export function MarketResearchDashboard({ businessId, data, onRefresh }) {
    const snapshot = data?.snapshot || null;
    const marketData = data?.market || null;
    const isLive = !!data && !!snapshot;
    const isCached = data?.cached;
    const timestamp = data?.timestamp;

    const metrics = deriveMetrics(snapshot);
    const trends = deriveTrends(snapshot, marketData);
    const insights = deriveInsights(snapshot, marketData);

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
                        <div className="flex items-center gap-2 mt-0.5">
                            <p className="mo-text-secondary">AI-powered market analysis & growth opportunities</p>
                            {isLive ? (
                                <span className="flex items-center gap-1 text-xs text-[#4CBB17]">
                                    <Wifi className="h-3 w-3" />
                                    {isCached ? "Cached" : "Live"}
                                </span>
                            ) : (
                                <span className="flex items-center gap-1 text-xs text-[#A0A0A0]">
                                    <WifiOff className="h-3 w-3" /> Demo
                                </span>
                            )}
                        </div>
                        {timestamp && (
                            <p className="text-[10px] text-[#555] mt-0.5">
                                Last updated: {new Date(timestamp).toLocaleTimeString()}
                            </p>
                        )}
                    </div>
                </div>
                <button onClick={onRefresh} className="mo-btn-secondary flex items-center gap-2 text-sm">
                    <RefreshCw className="h-4 w-4" /> Refresh
                </button>
            </div>

            {/* Key Metrics — derived from real snapshot */}
            <div className="grid gap-4 md:grid-cols-4">
                <StatCard
                    label="Revenue Growth"
                    value={`+${metrics.revenueGrowth}%`}
                    sub={isLive ? `₹${(snapshot?.revenue || 0).toLocaleString('en-IN')} revenue` : "vs last quarter"}
                    accent="#4CBB17"
                />
                <StatCard
                    label="Profit Margin"
                    value={isLive ? `${snapshot?.profit_margin || 0}%` : `${metrics.marketShare}%`}
                    sub={isLive ? `₹${(snapshot?.net_profit || 0).toLocaleString('en-IN')} net profit` : "Estimated"}
                    accent={isLive && (snapshot?.profit_margin || 0) > 40 ? "#4CBB17" : "#ffffff"}
                />
                <StatCard
                    label="Growth Opportunity"
                    value={`${metrics.opportunityScore}/100`}
                    sub={isLive ? `${snapshot?.client_count || snapshot?.totalClients || snapshot?.active_clients || snapshot?.total_clients || 0} active clients` : "Potential score"}
                    accent="#60A5FA"
                />
                <StatCard
                    label="Competitive Position"
                    value={metrics.competitiveRank}
                    sub={isLive
                        ? `${snapshot?.overdue_count || 0} overdue invoices`
                        : "In your sector"
                    }
                    accent={isLive && (snapshot?.overdue_count || 0) > 0 ? "#CD1C18" : "#ffffff"}
                />
            </div>

            {/* Transaction Pattern Analysis — from real invoice data */}
            <div className="mo-card">
                <h2 className="mo-h2 mb-1">Transaction Pattern Analysis</h2>
                <p className="mo-text-secondary mb-4">
                    {isLive
                        ? `Derived from ${snapshot?.total_invoices || 0} invoices across ${snapshot?.total_clients || 0} clients`
                        : "Market trends derived from your business transactions"
                    }
                </p>
                <div className="flex flex-col gap-3">
                    {trends.length > 0 ? trends.map((trend, i) => (
                        <div key={i} className="flex items-center justify-between p-3 rounded-xl border border-[#2A2A2A] hover:border-[#3A3A3A] transition-all">
                            <div className="flex items-center gap-3">
                                <div className="h-2 w-2 rounded-full flex-shrink-0"
                                    style={{ backgroundColor: trend.isLive ? "#FFB300" : trend.direction === "up" ? "#4CBB17" : "#CD1C18" }}
                                />
                                <div>
                                    <div className="flex items-center gap-2">
                                        <p className="font-semibold text-white text-sm">{formatIndustryName(trend.category)}</p>
                                        {trend.isLive && (
                                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#FFB30020] text-[#FFB300] border border-[#FFB30040]">LIVE</span>
                                        )}
                                    </div>
                                    <p className="text-xs text-[#A0A0A0]">{trend.description}</p>
                                </div>
                            </div>
                            <div className="text-right flex-shrink-0">
                                {trend.amount > 0 && (
                                    <p className="font-semibold text-white text-sm">₹{trend.amount.toLocaleString('en-IN')}</p>
                                )}
                                {trend.change !== null && trend.change !== undefined && (
                                    <div className={`text-xs flex items-center justify-end gap-1 ${trend.direction === "up" ? "text-[#4CBB17]" : "text-[#CD1C18]"}`}>
                                        {trend.direction === "up" ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                                        {trend.change}%
                                    </div>
                                )}
                            </div>
                        </div>
                    )) : (
                        <p className="text-sm text-[#A0A0A0] text-center py-4">No transaction data yet</p>
                    )}
                </div>
            </div>

            {/* AI Insights — from real Tavily data */}
            <div className="mo-card">
                <div className="flex items-center justify-between mb-1">
                    <h2 className="mo-h2">AI Market Insights & Recommendations</h2>
                    {isLive && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#4CBB1720] text-[#4CBB17] border border-[#4CBB1740]">
                            Powered by Live Data
                        </span>
                    )}
                </div>
                <p className="mo-text-secondary mb-4">
                    {isLive ? "Real-time analysis from Tavily + your business metrics" : "AI-powered analysis of your market position"}
                </p>
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
                                        <span className={`text-xs px-2 py-0.5 rounded-md font-medium border ${PRIORITY_BADGE[insight.priority] || PRIORITY_BADGE.low}`}>
                                            {insight.priority}
                                        </span>
                                        <span className="font-semibold text-white text-sm">{insight.title}</span>
                                    </div>
                                    <p className="text-sm text-[#A0A0A0]">{insight.message}</p>
                                    {insight.action && (
                                        <button
                                            className="mt-2 text-xs text-[#4CBB17] hover:underline font-medium"
                                            onClick={() => insight.link && window.location.assign(insight.link)}
                                        >
                                            {insight.action} →
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Live News Feed — only when real data available */}
            {isLive && marketData?.news?.news?.length > 0 && (
                <div className="mo-card">
                    <h2 className="mo-h2 mb-1">Live Market News</h2>
                    <p className="mo-text-secondary mb-4">Latest headlines affecting your business sector</p>
                    <div className="flex flex-col gap-2">
                        {marketData.news.news.slice(0, 5).map((headline, i) => (
                            <div key={i} className="flex items-start gap-2 p-2 rounded-lg hover:bg-[#1A1A1A] transition-all">
                                <span className="text-[#FFB300] text-xs mt-0.5 flex-shrink-0">●</span>
                                <p className="text-xs text-[#A0A0A0] leading-relaxed">{headline}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
