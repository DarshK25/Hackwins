import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, TrendingUp, AlertCircle } from "lucide-react";

export function MarketResearchDashboard({ businessId, data, onRefresh }) {
    // Mock fallback data
    const mockData = {
        metrics: {
            revenueGrowth: 15,
            marketShare: 12,
            opportunityScore: 82,
            competitiveRank: "#3",
        },
        trends: [
            {
                category: "fintech_services",
                description: "Adoption of automated compliance tools",
                amount: 2500000,
                direction: "up",
                change: 35,
            },
            {
                category: "consulting",
                description: "Shift towards remote advisory",
                amount: 850000,
                direction: "up",
                change: 12,
            },
            {
                category: "legacy_software",
                description: "Declining interest in on-premise solutions",
                amount: 450000,
                direction: "down",
                change: 8,
            },
        ],
        insights: [
            {
                priority: "high",
                title: "Emerging Market Gap",
                message:
                    "SME sector is underserved for automated GST filing in the western region.",
                action: "Review Strategy",
            },
            {
                priority: "medium",
                title: "Regulatory Change",
                message: "New tax compliance deadline extended by 30 days.",
                action: "View Details",
            },
            {
                priority: "medium",
                title: "Competitor Movement",
                message: "Competitor X has raised prices by 15%. Opportunity to capture share.",
                action: "Target New Clients",
            },
        ],
    };

    const activeData = data || mockData;
    const metrics = activeData.metrics || {};
    const trends = activeData.trends || [];
    const insights = activeData.insights || [];

    // Helper to format industry names
    const formatIndustryName = (industry) => {
        return industry
            .split("_")
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(" & ");
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-3xl font-bold">🔍 Market Research Intelligence</h2>
                    <p className="text-muted-foreground">
                        AI-powered market analysis & growth opportunities
                    </p>
                </div>
                <Button onClick={onRefresh} variant="outline">
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Refresh
                </Button>
            </div>

            {/* Key Metrics */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Revenue Growth</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-600">
                            +{metrics.revenueGrowth || 0}%
                        </div>
                        <p className="text-xs text-muted-foreground">vs last quarter</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Market Share</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{metrics.marketShare || 0}%</div>
                        <p className="text-xs text-muted-foreground">Estimated</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            Growth Opportunity
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-blue-600">
                            {metrics.opportunityScore || 0}/100
                        </div>
                        <p className="text-xs text-muted-foreground">Potential score</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            Competitive Position
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {metrics.competitiveRank || "N/A"}
                        </div>
                        <p className="text-xs text-muted-foreground">In your sector</p>
                    </CardContent>
                </Card>
            </div>

            {/* Transaction Trends */}
            <Card>
                <CardHeader>
                    <CardTitle>Transaction Pattern Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {trends.map((trend, i) => (
                            <div
                                key={i}
                                className="flex items-center justify-between p-4 border rounded-lg"
                            >
                                <div className="flex items-center gap-3">
                                    <div
                                        className={`w-2 h-2 rounded-full ${trend.direction === "up" ? "bg-green-500" : "bg-red-500"
                                            }`}
                                    ></div>
                                    <div>
                                        <div className="font-medium">
                                            {formatIndustryName(trend.category)}
                                        </div>
                                        <div className="text-sm text-muted-foreground">
                                            {trend.description}
                                        </div>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <div className="font-semibold">
                                        ₹{trend.amount.toLocaleString()}
                                    </div>
                                    <div
                                        className={`text-xs flex items-center gap-1 ${trend.direction === "up" ? "text-green-600" : "text-red-600"
                                            }`}
                                    >
                                        <TrendingUp className="h-3 w-3" />
                                        {trend.change}%
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* AI Insights */}
            <Card>
                <CardHeader>
                    <CardTitle>🤖 AI Market Insights & Recommendations</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {insights.map((insight, i) => (
                            <div
                                key={i}
                                className={`p-4 border-2 rounded-lg ${insight.priority === "high"
                                    ? "border-blue-500"
                                    : insight.priority === "medium"
                                        ? "border-yellow-500"
                                        : "border-gray-300"
                                    }`}
                            >
                                <div className="flex items-start gap-3">
                                    {insight.priority === "high" && (
                                        <AlertCircle className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                                    )}
                                    <div className="flex-1">
                                        <div className="font-semibold text-foreground">
                                            {insight.title}
                                        </div>
                                        <div className="text-sm text-foreground/80 mt-1">
                                            {insight.message}
                                        </div>
                                        {insight.action && (
                                            <Button
                                                variant="link"
                                                className="p-0 h-auto mt-2 text-primary"
                                                onClick={() => {
                                                    // Navigate based on action
                                                    const action = insight.action;
                                                    if (action === "Create Invoice") {
                                                        window.location.href = "/invoices"; // Corrected path
                                                    } else if (action === "View Analytics") {
                                                        window.location.href = "/analytics"; // Corrected path
                                                    } else if (
                                                        action === "Scale Operations" ||
                                                        action === "Explore Opportunities"
                                                    ) {
                                                        window.location.href = "/clients"; // Corrected path
                                                    } else if (action === "Review Strategy") {
                                                        window.location.href = "/analytics"; // Corrected path
                                                    } else if (
                                                        action === "Prepare for Year-End" ||
                                                        action === "Target New Clients"
                                                    ) {
                                                        window.location.href = "/clients"; // Corrected path
                                                    } else if (action === "View Details") {
                                                        // Open compliance/tax resources
                                                        window.open(
                                                            "https://www.incometax.gov.in/iec/foportal",
                                                            "_blank"
                                                        );
                                                    }
                                                }}
                                            >
                                                {insight.action} →
                                            </Button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
