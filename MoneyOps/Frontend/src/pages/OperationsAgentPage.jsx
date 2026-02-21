import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Cog, Zap, Bot, Clock, RefreshCw } from "lucide-react";
import { useOrganization, useAuth } from "@clerk/clerk-react";
import { toast } from "sonner";

const AI_GATEWAY_URL = import.meta.env.VITE_AI_GATEWAY_URL || "http://localhost:8000";

export default function OperationsAgentPage() {
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
                    session_id: `ops-${Date.now()}`,
                    context: {}
                })
            });
            const data = await res.json();
            setResults(prev => ({ ...prev, [toolName]: data }));
            toast.success("Operations analysis complete");
        } catch (err) {
            toast.error(`Failed: ${err.message}`);
        } finally {
            setLoading(prev => ({ ...prev, [toolName]: false }));
        }
    };

    const EfficiencyResult = ({ data }) => {
        if (!data?.data) return null;
        const { efficiency_score, bottlenecks, quick_wins } = data.data;
        return (
            <div className="space-y-3 mt-3">
                {efficiency_score !== undefined && (
                    <div className="rounded-xl bg-gradient-to-br from-orange-500/20 to-amber-500/10 border border-orange-500/30 p-4 text-center">
                        <div className="text-5xl font-black text-orange-400">{efficiency_score}</div>
                        <div className="text-xs text-white/50 mt-1">Efficiency Score / 100</div>
                    </div>
                )}
                {bottlenecks?.length > 0 && (
                    <div className="space-y-2">
                        <div className="text-xs font-semibold text-white/50 uppercase">Bottlenecks</div>
                        {bottlenecks.map((b, i) => (
                            <div key={i} className="rounded-xl bg-red-500/10 border border-red-500/20 p-3">
                                <div className="font-semibold text-red-400 text-sm mb-1">{b.issue}</div>
                                <div className="text-xs text-white/60 mb-1">{b.impact}</div>
                                <div className="text-xs text-primary">{b.solution}</div>
                            </div>
                        ))}
                    </div>
                )}
                {quick_wins?.length > 0 && (
                    <div className="space-y-2">
                        <div className="text-xs font-semibold text-white/50 uppercase">Quick Wins</div>
                        {quick_wins.map((w, i) => (
                            <div key={i} className="rounded-xl bg-green-500/10 border border-green-500/20 p-3">
                                <div className="flex justify-between mb-1">
                                    <div className="font-semibold text-green-400 text-sm">{w.action}</div>
                                    <Badge className="bg-green-500/20 text-green-300 text-xs">{w.timeframe}</Badge>
                                </div>
                                <div className="text-xs text-primary">{w.impact}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    };

    const AutomationResult = ({ data }) => {
        if (!data?.data?.automation_opportunities) return null;
        const { automation_opportunities, estimated_savings } = data.data;
        return (
            <div className="space-y-3 mt-3">
                {estimated_savings && (
                    <div className="rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/10 border border-blue-500/30 p-4">
                        <div className="text-center mb-2">
                            <div className="text-2xl font-bold text-blue-400">{estimated_savings.hours_saved_monthly} hrs/mo</div>
                            <div className="text-xs text-white/50">Time Saved</div>
                        </div>
                        <div className="text-center">
                            <div className="text-2xl font-bold text-green-400">₹{estimated_savings.cost_saved_monthly?.toLocaleString()}/mo</div>
                            <div className="text-xs text-white/50">Cost Saved</div>
                        </div>
                    </div>
                )}
                {automation_opportunities?.map((opp, i) => (
                    <div key={i} className="rounded-xl bg-white/5 border border-white/10 p-3">
                        <div className="flex items-center justify-between mb-1">
                            <div className="font-semibold text-white text-sm">{opp.process}</div>
                            <Badge className="bg-blue-500/20 text-blue-300 text-xs">{opp.priority}</Badge>
                        </div>
                        <div className="text-xs text-white/60 mb-1">{opp.time_saved_hours}h/mo saved</div>
                        <div className="text-xs text-primary">{opp.tool_recommendation}</div>
                    </div>
                ))}
            </div>
        );
    };

    const tools = [
        { key: "efficiency", label: "Efficiency Analysis", prompt: "Analyze my business process efficiency", icon: <Zap className="h-5 w-5" />, color: "from-orange-500 to-amber-600", ResultComponent: EfficiencyResult },
        { key: "automation", label: "Automation Opportunities", prompt: "Find automation opportunities in my operations", icon: <Bot className="h-5 w-5" />, color: "from-blue-500 to-cyan-600", ResultComponent: AutomationResult },
    ];

    return (
        <div className="flex flex-col h-full bg-gradient-to-br from-slate-950 via-orange-950/20 to-slate-950 p-6 space-y-6">
            <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-gradient-to-br from-orange-500 to-amber-600 shadow-lg shadow-orange-500/30">
                    <Cog className="h-6 w-6 text-white" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold text-white">Operations Agent</h1>
                    <p className="text-white/50 text-sm">Process efficiency, bottleneck detection, automation opportunities</p>
                </div>
                <Badge className="bg-orange-500/20 text-orange-300 border border-orange-500/30">Operations Intelligence</Badge>
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
