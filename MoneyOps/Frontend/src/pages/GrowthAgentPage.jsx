import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Rocket, Tag, MapPin, BarChart3, RefreshCw } from "lucide-react";
import { useOrganization, useAuth } from "@clerk/clerk-react";
import { toast } from "sonner";

const AI_GATEWAY_URL = import.meta.env.VITE_AI_GATEWAY_URL || "http://localhost:8000";

export default function GrowthAgentPage() {
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
                    session_id: `growth-${Date.now()}`,
                    context: {}
                })
            });
            const data = await res.json();
            setResults(prev => ({ ...prev, [toolName]: data }));
            toast.success("Growth analysis complete");
        } catch (err) {
            toast.error(`Failed: ${err.message}`);
        } finally {
            setLoading(prev => ({ ...prev, [toolName]: false }));
        }
    };

    const PricingResult = ({ data }) => {
        if (!data?.data) return null;
        const { current_avg_price, recommended_price, pricing_tiers, justification } = data.data;
        return (
            <div className="space-y-3 mt-3">
                {current_avg_price && recommended_price && (
                    <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-xl bg-white/5 border border-white/10 p-3 text-center">
                            <div className="text-2xl font-bold text-white">₹{current_avg_price?.toLocaleString()}</div>
                            <div className="text-xs text-white/50">Current Avg Price</div>
                        </div>
                        <div className="rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-500/10 border border-green-500/30 p-3 text-center">
                            <div className="text-2xl font-bold text-green-400">₹{recommended_price?.toLocaleString()}</div>
                            <div className="text-xs text-white/50">Recommended Price</div>
                        </div>
                    </div>
                )}
                {pricing_tiers?.map((tier, i) => (
                    <div key={i} className="rounded-xl bg-white/5 border border-white/10 p-3">
                        <div className="flex items-center justify-between mb-1">
                            <div className="font-semibold text-white text-sm">{tier.tier}</div>
                            <div className="text-primary font-bold">₹{tier.price?.toLocaleString()}</div>
                        </div>
                        <p className="text-xs text-white/60 mb-1">{tier.description}</p>
                        <div className="text-xs text-green-400">{tier.projected_revenue}</div>
                    </div>
                ))}
                {justification && (
                    <div className="rounded-xl bg-white/5 border border-white/10 p-3 text-xs text-white/60">{justification}</div>
                )}
            </div>
        );
    };

    const ExpansionResult = ({ data }) => {
        if (!data?.data?.opportunities) return null;
        const { opportunities, total_addressable_market } = data.data;
        return (
            <div className="space-y-3 mt-3">
                {total_addressable_market && (
                    <div className="rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/10 border border-blue-500/30 p-4 text-center">
                        <div className="text-2xl font-bold text-white">{total_addressable_market}</div>
                        <div className="text-xs text-white/50">Total Addressable Market</div>
                    </div>
                )}
                {opportunities?.map((opp, i) => (
                    <div key={i} className="rounded-xl bg-white/5 border border-white/10 p-4">
                        <div className="flex items-center justify-between mb-2">
                            <div className="font-semibold text-white text-sm">{opp.market}</div>
                            <Badge className="bg-blue-500/20 text-blue-300 text-xs">{opp.estimated_revenue}</Badge>
                        </div>
                        <div className="flex gap-2 mb-2">
                            <Badge className={`text-xs ${opp.difficulty === "Low" ? "bg-green-500/20 text-green-300" : opp.difficulty === "Medium" ? "bg-yellow-500/20 text-yellow-300" : "bg-red-500/20 text-red-300"}`}>
                                {opp.difficulty} Difficulty
                            </Badge>
                            <Badge className="bg-white/10 text-white/50 text-xs">{opp.timeframe}</Badge>
                        </div>
                        <ul className="space-y-1">
                            {opp.steps?.map((s, j) => <li key={j} className="text-xs text-white/60">→ {s}</li>)}
                        </ul>
                    </div>
                ))}
            </div>
        );
    };

    const tools = [
        { key: "pricing", label: "Pricing Optimization", prompt: "Optimize my pricing strategy", icon: <Tag className="h-5 w-5" />, color: "from-green-500 to-emerald-600", ResultComponent: PricingResult },
        { key: "expansion", label: "Market Expansion", prompt: "Identify market expansion opportunities", icon: <MapPin className="h-5 w-5" />, color: "from-blue-500 to-cyan-600", ResultComponent: ExpansionResult },
    ];

    return (
        <div className="flex flex-col h-full bg-gradient-to-br from-slate-950 via-green-950/20 to-slate-950 p-6 space-y-6">
            <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 shadow-lg shadow-green-500/30">
                    <Rocket className="h-6 w-6 text-white" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold text-white">Growth Agent</h1>
                    <p className="text-white/50 text-sm">Pricing optimization, market expansion, revenue modeling</p>
                </div>
                <Badge className="bg-green-500/20 text-green-300 border border-green-500/30">Growth Intelligence</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
                                    {loading[tool.key] ? <RefreshCw className="h-3 w-3 animate-spin" /> : "Analyze"}
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            {results[tool.key] ? (
                                <tool.ResultComponent data={results[tool.key]} />
                            ) : (
                                <div className="text-center py-10 text-white/30">
                                    <div className="flex justify-center mb-2 opacity-30">{tool.icon}</div>
                                    <p className="text-sm">Click Analyze to generate insights</p>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}
