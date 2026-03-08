import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Users, UserX, Star, TrendingDown, RefreshCw, Heart } from "lucide-react";
import { useOrganization, useAuth } from "@clerk/clerk-react";
import { toast } from "sonner";

const AI_GATEWAY_URL = ""; // Use Vite proxy via relative paths (/api/v1)

export default function CustomerAgentPage() {
    const { organization } = useOrganization();
    const { getToken } = useAuth();
    const [loading, setLoading] = useState({});
    const [results, setResults] = useState({});

    const callAgent = async (toolName, prompt) => {
        setLoading(prev => ({ ...prev, [toolName]: true }));
        try {
            const token = await getToken();
            const res = await fetch(`${AI_GATEWAY_URL}/api/v1/voice/process`, {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({
                    text: prompt,
                    user_id: "user",
                    org_id: organization?.id || "default_org",
                    session_id: `customer-${Date.now()}`,
                    context: {}
                })
            });
            const data = await res.json();
            setResults(prev => ({ ...prev, [toolName]: data }));
            toast.success("Analysis complete");
        } catch (err) {
            toast.error(`Failed: ${err.message}`);
        } finally {
            setLoading(prev => ({ ...prev, [toolName]: false }));
        }
    };

    const ChurnResult = ({ data }) => {
        if (!data?.data) return null;
        const { churn_risk_summary, at_risk_clients } = data.data;
        return (
            <div className="space-y-3 mt-3">
                {churn_risk_summary && (
                    <div className="grid grid-cols-3 gap-2">
                        {[
                            { label: "High Risk", value: churn_risk_summary.high_risk, color: "text-red-400" },
                            { label: "Medium Risk", value: churn_risk_summary.medium_risk, color: "text-yellow-400" },
                            { label: "Low Risk", value: churn_risk_summary.low_risk, color: "text-green-400" },
                        ].map(item => (
                            <div key={item.label} className="text-center rounded-xl bg-white/5 border border-white/10 p-3">
                                <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
                                <div className="text-xs text-white/50">{item.label}</div>
                            </div>
                        ))}
                    </div>
                )}
                {at_risk_clients?.slice(0, 5).map((c, i) => (
                    <div key={i} className="rounded-xl bg-white/5 border border-white/10 p-3">
                        <div className="flex items-center justify-between mb-1">
                            <div className="font-semibold text-white text-sm">{c.name}</div>
                            <Badge className={c.churn_risk === "high" ? "bg-red-500/20 text-red-300" : "bg-yellow-500/20 text-yellow-300"}>
                                {c.churn_risk?.toUpperCase()} RISK
                            </Badge>
                        </div>
                        <div className="text-xs text-white/50 mb-2">{c.churn_reason}</div>
                        <div className="text-xs text-primary">{c.intervention}</div>
                    </div>
                ))}
            </div>
        );
    };

    const CLVResult = ({ data }) => {
        if (!data?.data) return null;
        const { total_portfolio_value, clients } = data.data;
        return (
            <div className="space-y-3 mt-3">
                {total_portfolio_value && (
                    <div className="rounded-xl bg-gradient-to-br from-purple-500/20 to-violet-500/10 border border-purple-500/30 p-4 text-center">
                        <div className="text-3xl font-black text-white">₹{total_portfolio_value.toLocaleString()}</div>
                        <div className="text-xs text-white/50 mt-1">Total Portfolio CLV</div>
                    </div>
                )}
                {clients?.slice(0, 5).map((c, i) => (
                    <div key={i} className="rounded-xl bg-white/5 border border-white/10 p-3">
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="font-semibold text-white text-sm">{c.name}</div>
                                <div className="text-xs text-white/50">{c.segment}</div>
                            </div>
                            <div className="text-right">
                                <div className="text-sm font-bold text-primary">₹{c.clv?.toLocaleString()}</div>
                                <div className="text-xs text-white/40">CLV</div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        );
    };

    const SegmentResult = ({ data }) => {
        if (!data?.data?.segments) return null;
        const { segments } = data.data;
        const segColors = {
            Champions: "from-emerald-500/20 to-green-500/10 border-emerald-500/30 text-emerald-400",
            "Loyal Customers": "from-blue-500/20 to-cyan-500/10 border-blue-500/30 text-blue-400",
            "At Risk": "from-red-500/20 to-rose-500/10 border-red-500/30 text-red-400",
            "Lost Customers": "from-gray-500/20 to-slate-500/10 border-gray-500/30 text-gray-400",
        };
        return (
            <div className="space-y-3 mt-3">
                {segments?.map((seg, i) => (
                    <div key={i} className={`rounded-xl bg-gradient-to-br ${segColors[seg.segment] || "from-white/5 to-white/2 border-white/10 text-white"} border p-4`}>
                        <div className="flex items-center justify-between mb-2">
                            <div className="font-semibold text-sm">{seg.segment}</div>
                            <Badge className="bg-white/10 text-white/70 text-xs">{seg.count} clients</Badge>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-xs text-white/60">
                            <div>Revenue: ₹{seg.total_revenue?.toLocaleString()}</div>
                            <div>Avg: ₹{seg.avg_value?.toLocaleString()}</div>
                        </div>
                        <div className="text-xs text-white/50 mt-2">{seg.action}</div>
                    </div>
                ))}
            </div>
        );
    };

    const tools = [
        { key: "churn", label: "Churn Prediction", prompt: "Predict customer churn risk", icon: <UserX className="h-5 w-5" />, color: "from-red-500 to-rose-600", ResultComponent: ChurnResult },
        { key: "clv", label: "Customer Lifetime Value", prompt: "Calculate customer lifetime value", icon: <Star className="h-5 w-5" />, color: "from-purple-500 to-violet-600", ResultComponent: CLVResult },
        { key: "segment", label: "Customer Segmentation", prompt: "Segment my customers by value", icon: <Users className="h-5 w-5" />, color: "from-blue-500 to-cyan-600", ResultComponent: SegmentResult },
    ];

    return (
        <div className="flex flex-col h-full bg-gradient-to-br from-slate-950 via-purple-950/20 to-slate-950 p-6 space-y-6">
            <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 shadow-lg shadow-purple-500/30">
                    <Heart className="h-6 w-6 text-white" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold text-white">Customer Agent</h1>
                    <p className="text-white/50 text-sm">Churn prediction, CLV analysis, and customer intelligence</p>
                </div>
                <Badge className="bg-purple-500/20 text-purple-300 border border-purple-500/30">Customer Intelligence</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {tools.map(tool => (
                    <Card key={tool.key} className="bg-white/5 border-white/10 hover:border-white/20 transition-all duration-300">
                        <CardHeader className="pb-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className={`p-2 rounded-xl bg-gradient-to-br ${tool.color}`}>
                                        <div className="text-white">{tool.icon}</div>
                                    </div>
                                    <CardTitle className="text-white text-sm">{tool.label}</CardTitle>
                                </div>
                                <Button size="sm" onClick={() => callAgent(tool.key, tool.prompt)} disabled={loading[tool.key]}
                                    className={`bg-gradient-to-r ${tool.color} text-white border-0 hover:opacity-90`}>
                                    {loading[tool.key] ? <RefreshCw className="h-3 w-3 animate-spin" /> : "Run"}
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            {results[tool.key] ? (
                                <tool.ResultComponent data={results[tool.key]} />
                            ) : (
                                <div className="text-center py-8 text-white/30">
                                    <div className="flex justify-center mb-2">{tool.icon}</div>
                                    <p className="text-sm">Click Run to analyze</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}
