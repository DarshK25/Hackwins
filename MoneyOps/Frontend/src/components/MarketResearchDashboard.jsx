import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    RefreshCw,
    TrendingUp,
    AlertCircle,
    Wifi,
    WifiOff,
    Newspaper,
    Radar,
    Building2,
    BriefcaseBusiness,
    ExternalLink,
    ChevronDown,
    ChevronUp,
} from "lucide-react";

const PRIORITY_BADGE = {
    high: "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]",
    medium: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
    low: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
};

const BLOCKED_DOMAINS = [
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "pinterest.com",
    "revenueml.com",
];

const NOISE_PATTERNS = [
    /join now/i,
    /sign in/i,
    /report this article/i,
    /report this comment/i,
    /see more comments/i,
    /like\]/i,
    /reply\]/i,
    /comment\]/i,
    /cold-join/i,
    /guest-reporting/i,
];

function toArray(value) {
    return Array.isArray(value) ? value : [];
}

function domainFromUrl(url) {
    try {
        return new URL(url).hostname.replace(/^www\./, "");
    } catch {
        return "source";
    }
}

function buildBusinessKeywords(profile) {
    const source = [
        profile?.industry_label,
        profile?.activity_label,
        ...(profile?.services || []),
        profile?.target_market,
        profile?.state,
        profile?.city,
    ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

    return [...new Set(
        source
            .split(/[^a-z0-9]+/i)
            .map((token) => token.trim())
            .filter((token) => token.length > 3)
            .filter((token) => !["with", "from", "that", "this", "across", "design", "supply", "annual", "india"].includes(token))
    )];
}

function isRelevantText(text, keywords) {
    const haystack = String(text || "").toLowerCase();
    if (!haystack) return false;
    const hits = keywords.filter((keyword) => haystack.includes(keyword));
    return hits.length >= 2 || (hits.length >= 1 && /ev|charging|fleet|subsidy|audit|infra|infrastructure|mobility|energy|utilities|charger/.test(haystack));
}

function cleanSnippet(text) {
    if (!text) return "";
    return String(text)
        .replace(/\[[^\]]+\]\(([^)]+)\)/g, " ")
        .replace(/https?:\/\/\S+/g, " ")
        .replace(/[#*_`>]/g, " ")
        .replace(/\s+/g, " ")
        .replace(/\b(Like|Reply|Comment|Follow|Report this article|Report this comment|See more comments|Skip to content|Table of Contents|Receive Pricing Insights Direct to Your Inbox|We value your privacy|Accept All)\b/gi, " ")
        .trim();
}

function summarizeSnippet(text, maxLength = 220) {
    const cleaned = cleanSnippet(text);
    if (!cleaned) return "";
    const firstSentence = cleaned.split(/(?<=[.!?])\s+/)[0] || cleaned;
    const candidate = firstSentence.length > 80 ? firstSentence : cleaned;
    if (candidate.length <= maxLength) return candidate;
    return `${candidate.slice(0, maxLength).trim()}...`;
}

function isUsableCitation(item) {
    const domain = domainFromUrl(item.url || "");
    const text = `${item.title || ""} ${item.snippet || ""}`;
    if (!item.url || !item.title) return false;
    if (BLOCKED_DOMAINS.some((blocked) => domain.includes(blocked))) return false;
    if (NOISE_PATTERNS.some((pattern) => pattern.test(text))) return false;
    return true;
}

function sourceWeight(domain) {
    if (/\.gov|\.nic\.in|ibef\.org|livemint\.com|forbesindia\.com|business-standard\.com|thehindu\.com|mint\.com/.test(domain)) return 3;
    if (/\.org|\.edu|\.com/.test(domain)) return 2;
    return 1;
}

function collectCitations(marketData, profile) {
    const keywords = buildBusinessKeywords(profile);
    const citations = [];

    toArray(marketData?.opportunities?.results).forEach((item) => {
        const snippet = cleanSnippet(item.content || "");
        const text = `${item.title || ""} ${snippet}`;
        if (!isRelevantText(text, keywords)) return;
        citations.push({
            type: "opportunity",
            title: item.title || "Opportunity source",
            snippet,
            url: item.url || "",
            source: domainFromUrl(item.url),
        });
    });

    toArray(marketData?.competitors?.moves_results).forEach((item) => {
        const snippet = cleanSnippet(item.content || "");
        const text = `${item.title || ""} ${snippet}`;
        if (!isRelevantText(text, keywords)) return;
        citations.push({
            type: "competitor",
            title: item.title || "Competitor source",
            snippet,
            url: item.url || "",
            source: domainFromUrl(item.url),
        });
    });

    toArray(marketData?.news?.raw_results).forEach((item) => {
        const snippet = cleanSnippet(item.content || "");
        const text = `${item.title || ""} ${snippet}`;
        if (!isRelevantText(text, keywords)) return;
        citations.push({
            type: "news",
            title: item.title || "News source",
            snippet,
            url: item.url || "",
            source: domainFromUrl(item.url),
        });
    });

    toArray(marketData?.news?.news_items).forEach((item) => {
        const snippet = cleanSnippet(item.description || "");
        const text = `${item.title || ""} ${snippet}`;
        if (!isRelevantText(text, keywords)) return;
        citations.push({
            type: "news",
            title: item.title || "News source",
            snippet,
            url: item.url || "",
            source: item.source || domainFromUrl(item.url),
            publishedAt: item.published_at || "",
        });
    });

    const deduped = [];
    const seen = new Set();
    citations.forEach((item) => {
        const key = `${item.title}|${item.url}`;
        if (seen.has(key) || !isUsableCitation(item)) return;
        seen.add(key);
        deduped.push(item);
    });

    return deduped
        .sort((a, b) => sourceWeight(b.source) - sourceWeight(a.source))
        .slice(0, 8);
}

function deriveSignals(citations) {
    const grouped = {
        opportunity: citations.filter((item) => item.type === "opportunity"),
        competitor: citations.filter((item) => item.type === "competitor"),
        news: citations.filter((item) => item.type === "news"),
    };

    const signals = [];

    if (grouped.opportunity[0]) {
        signals.push({
            label: "Demand signal",
            text: summarizeSnippet(grouped.opportunity[0].snippet || grouped.opportunity[0].title, 180),
            icon: TrendingUp,
            accent: "#4CBB17",
            citation: grouped.opportunity[0],
        });
    }

    if (grouped.competitor[0]) {
        signals.push({
            label: "Competitor watch",
            text: summarizeSnippet(grouped.competitor[0].snippet || grouped.competitor[0].title, 180),
            icon: Radar,
            accent: "#FFB300",
            citation: grouped.competitor[0],
        });
    }

    grouped.news.slice(0, 2).forEach((item) => {
        signals.push({
            label: "Market headline",
            text: item.title,
            icon: Newspaper,
            accent: "#60A5FA",
            citation: item,
        });
    });

    return signals.slice(0, 4);
}

function deriveInsights(snapshot, profile, citations) {
    const insights = [];
    const topService = profile?.services?.[0] || profile?.activity_label || "your core service";
    const region = profile?.state || profile?.region || "your main region";
    const opportunity = citations.find((item) => item.type === "opportunity");
    const competitor = citations.find((item) => item.type === "competitor");
    const news = citations.find((item) => item.type === "news");

    if (opportunity) {
        insights.push({
            priority: "high",
            title: `Where demand looks strongest for ${topService}`,
            message: summarizeSnippet(opportunity.snippet || opportunity.title, 220),
            action: "Open source",
            url: opportunity.url,
            source: opportunity.source,
        });
    }

    if (competitor) {
        insights.push({
            priority: "medium",
            title: "Competitive movement to track",
            message: summarizeSnippet(competitor.snippet || competitor.title, 220),
            action: "Open source",
            url: competitor.url,
            source: competitor.source,
        });
    }

    if (news) {
        insights.push({
            priority: "medium",
            title: `Relevant live signal in ${region}`,
            message: news.title,
            action: "Open article",
            url: news.url,
            source: news.source,
        });
    }

    if ((snapshot?.overdue_count || 0) > 0) {
        insights.push({
            priority: "low",
            title: "Collections are limiting market moves",
            message: `${snapshot.overdue_count} overdue invoice${snapshot.overdue_count > 1 ? "s are" : " is"} tying up ₹${Number(snapshot?.overdue_amount || 0).toLocaleString("en-IN")}. Close those collections before pushing hard on new acquisition.`,
            action: "View overdue invoices",
            link: "/invoices?filter=overdue",
        });
    }

    if (!insights.length) {
        insights.push({
            priority: "medium",
            title: "No strong market matches yet",
            message: `Live research did not return enough high-confidence signals for ${profile?.business_name || "this business"} yet. The next pass should widen the buyer search around ${topService} in ${region}.`,
        });
    }

    return insights.slice(0, 4);
}

function deriveBuyerTargets(profile) {
    const serviceLabels = (profile?.services || []).slice(0, 3);
    const region = profile?.state || profile?.region || "your core market";

    const defaults = [
        `Commercial real-estate portfolios expanding EV parking in ${region}`,
        `Hotels, campuses, and institutions evaluating charger deployment or AMC coverage`,
        `Fleet-led operators needing readiness audits, subsidy guidance, or charging uptime support`,
    ];

    if (!serviceLabels.length) return defaults;

    return serviceLabels.map((service) => `${service} buyers across ${region}`);
}

function SourceLink({ item, label = "Open source" }) {
    if (!item?.url) return null;
    return (
        <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-[#4CBB17] hover:underline font-medium"
        >
            {label}
            <ExternalLink className="h-3 w-3" />
        </a>
    );
}

function CitationCard({ item }) {
    const [expanded, setExpanded] = useState(false);
    const preview = summarizeSnippet(item.snippet || item.title, 170);

    return (
        <div className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <p className="text-sm font-semibold text-white">{item.title}</p>
                    <p className="mt-1 text-xs text-[#A0A0A0]">
                        {item.source}
                        {item.publishedAt ? ` • ${new Date(item.publishedAt).toLocaleDateString()}` : ""}
                    </p>
                </div>
                <span className="rounded-md bg-[#1F1F1F] px-2 py-1 text-[10px] uppercase tracking-wide text-[#A0A0A0]">{item.type}</span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-[#D0D0D0]">{expanded ? item.snippet || item.title : preview}</p>
            <div className="mt-3 flex items-center justify-between gap-3">
                <button
                    type="button"
                    onClick={() => setExpanded((value) => !value)}
                    className="inline-flex items-center gap-1 text-xs text-[#A0A0A0] hover:text-white"
                >
                    {expanded ? "Collapse" : "Expand"}
                    {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                </button>
                <SourceLink item={item} label="Explore source" />
            </div>
        </div>
    );
}

export function MarketResearchDashboard({ businessId, data, onRefresh }) {
    const navigate = useNavigate();
    const [showAllSources, setShowAllSources] = useState(false);
    const snapshot = data?.snapshot || null;
    const marketData = data?.market || null;
    const profile = data?.profile || null;
    const isLive = !!data && !!snapshot;
    const isCached = data?.cached;
    const timestamp = data?.timestamp;

    const citations = useMemo(() => collectCitations(marketData, profile), [marketData, profile]);
    const signals = useMemo(() => deriveSignals(citations), [citations]);
    const insights = useMemo(() => deriveInsights(snapshot, profile, citations), [snapshot, profile, citations]);
    const buyerTargets = useMemo(() => deriveBuyerTargets(profile), [profile]);
    const visibleCitations = showAllSources ? citations : citations.slice(0, 4);

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-4">
                    <div className="rounded-xl p-3" style={{ backgroundColor: "#FFB30020", border: "1px solid #FFB30040" }}>
                        <TrendingUp className="h-6 w-6 text-[#FFB300]" />
                    </div>
                    <div>
                        <h1 className="mo-h1">Market Research Intelligence</h1>
                        <div className="flex items-center gap-2 mt-0.5">
                            <p className="mo-text-secondary">Live opportunities, competitor moves, and cited headlines filtered for your business.</p>
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
                        {timestamp && <p className="text-[10px] text-[#555] mt-0.5">Last updated: {new Date(timestamp).toLocaleTimeString()}</p>}
                    </div>
                </div>
                <button onClick={onRefresh} className="mo-btn-secondary flex items-center gap-2 text-sm">
                    <RefreshCw className="h-4 w-4" /> Refresh
                </button>
            </div>

            <div className="grid gap-4 xl:grid-cols-[1.2fr,0.8fr]">
                <div className="mo-card">
                    <div className="flex items-center justify-between mb-1">
                        <h2 className="mo-h2">AI Market Insights & Recommendations</h2>
                        {isLive && <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#4CBB1720] text-[#4CBB17] border border-[#4CBB1740]">Live context</span>}
                    </div>
                    <p className="mo-text-secondary mb-4">Each recommendation is tied to a usable source when one is available.</p>
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
                                        <div className="mt-2 flex items-center gap-3">
                                            {insight.action && insight.url && <SourceLink item={{ url: insight.url }} label={insight.action} />}
                                            {insight.action && insight.link && (
                                                <button className="text-xs text-[#4CBB17] hover:underline font-medium" onClick={() => navigate(insight.link)}>
                                                    {insight.action} →
                                                </button>
                                            )}
                                        </div>
                                        {insight.source && <p className="mt-2 text-[11px] text-[#777]">Source: {insight.source}</p>}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="mo-card">
                    <div className="flex items-center justify-between mb-1">
                        <h2 className="mo-h2">Where to Focus</h2>
                        <BriefcaseBusiness className="h-5 w-5 text-[#60A5FA]" />
                    </div>
                    <p className="mo-text-secondary mb-4">Suggested buyer lanes based on your services and geography.</p>
                    <div className="flex flex-col gap-3">
                        {buyerTargets.map((target, index) => (
                            <div key={index} className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
                                <div className="flex items-start gap-3">
                                    <Building2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-[#60A5FA]" />
                                    <p className="text-sm text-white">{target}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="mo-card">
                <div className="flex items-center justify-between mb-1">
                    <h2 className="mo-h2">Relevant Signals</h2>
                    <Radar className="h-5 w-5 text-[#60A5FA]" />
                </div>
                <p className="mo-text-secondary mb-4">Filtered live signals that match your business closely.</p>
                {signals.length > 0 ? (
                    <div className="grid gap-3 lg:grid-cols-2">
                        {signals.map((signal, index) => {
                            const Icon = signal.icon;
                            return (
                                <div key={index} className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
                                    <div className="mb-2 flex items-center gap-2">
                                        <Icon className="h-4 w-4" style={{ color: signal.accent }} />
                                        <span className="text-xs font-semibold uppercase tracking-wide text-[#A0A0A0]">{signal.label}</span>
                                    </div>
                                    <p className="text-sm leading-relaxed text-white">{signal.text}</p>
                                    <div className="mt-2">
                                        <SourceLink item={signal.citation} label="Explore source" />
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="rounded-xl border border-dashed border-[#2A2A2A] p-8 text-center">
                        <p className="text-sm text-[#A0A0A0]">No strong live signals matched your business profile yet.</p>
                    </div>
                )}
            </div>

            <div className="mo-card">
                <div className="flex items-center justify-between mb-1">
                    <h2 className="mo-h2">Cited Sources</h2>
                    <button
                        type="button"
                        onClick={() => setShowAllSources((value) => !value)}
                        className="inline-flex items-center gap-1 text-xs text-[#A0A0A0] hover:text-white"
                    >
                        {showAllSources ? "Show fewer" : `Show all ${citations.length}`}
                        {showAllSources ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </button>
                </div>
                <p className="mo-text-secondary mb-4">Expand a source for detail or open it directly.</p>
                {visibleCitations.length > 0 ? (
                    <div className="grid gap-3 lg:grid-cols-2">
                        {visibleCitations.map((item, i) => (
                            <CitationCard key={`${item.url}-${i}`} item={item} />
                        ))}
                    </div>
                ) : (
                    <div className="rounded-xl border border-dashed border-[#2A2A2A] p-8 text-center">
                        <p className="text-sm text-[#A0A0A0]">No strongly relevant cited sources matched this business profile yet.</p>
                    </div>
                )}
            </div>
        </div>
    );
}


