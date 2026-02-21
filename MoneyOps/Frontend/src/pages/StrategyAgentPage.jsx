import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Brain, Target, TrendingUp, AlertTriangle, CheckCircle2, 
  Lightbulb, Zap, Activity, BarChart3, RefreshCw 
} from "lucide-react";
import { useOrganization, useAuth } from "@clerk/clerk-react";
import { toast } from "sonner";

const AI_GATEWAY_URL = import.meta.env.VITE_AI_GATEWAY_URL || "http://localhost:8000";

export default function StrategyAgentPage() {
  const { organization } = useOrganization();
  const { getToken } = useAuth();
  const [loading, setLoading] = useState({});
  const [results, setResults] = useState({});

  const callAgent = async (toolName, label) => {
    setLoading(prev => ({ ...prev, [toolName]: true }));
    try {
      const token = await getToken();
      const orgId = organization?.id || "default_org";
      const res = await fetch(`${AI_GATEWAY_URL}/api/v1/voice/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({
          text: label,
          user_id: "user",
          org_id: orgId,
          session_id: `strategy-${Date.now()}`,
          context: {}
        })
      });
      const data = await res.json();
      setResults(prev => ({ ...prev, [toolName]: data }));
      toast.success(`${label} complete`);
    } catch (err) {
      toast.error(`Failed: ${err.message}`);
    } finally {
      setLoading(prev => ({ ...prev, [toolName]: false }));
    }
  };

  const HealthScore = ({ data }) => {
    if (!data?.data?.health_score) return null;
    const { health_score, status, components, recommendations, raw_metrics } = data.data;
    const color = health_score >= 75 ? "text-green-400" : health_score >= 50 ? "text-yellow-400" : "text-red-400";
    const bg = health_score >= 75 ? "from-green-500/20 to-emerald-500/10" : health_score >= 50 ? "from-yellow-500/20 to-orange-500/10" : "from-red-500/20 to-rose-500/10";

    return (
      <div className="space-y-4 mt-4">
        <div className={`rounded-2xl bg-gradient-to-br ${bg} border border-white/10 p-6 text-center`}>
          <div className={`text-7xl font-black ${color}`}>{health_score}</div>
          <div className="text-white/60 text-sm mt-1">Health Score / 100</div>
          <Badge className={`mt-2 ${health_score >= 75 ? "bg-green-500/20 text-green-300" : health_score >= 50 ? "bg-yellow-500/20 text-yellow-300" : "bg-red-500/20 text-red-300"}`}>
            {status?.toUpperCase()}
          </Badge>
        </div>
        {components && (
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(components).map(([key, comp]) => (
              <div key={key} className="rounded-xl bg-white/5 border border-white/10 p-3">
                <div className="text-xs text-white/50 mb-1">{comp.label}</div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 rounded-full bg-white/10">
                    <div className="h-2 rounded-full bg-gradient-to-r from-primary to-blue-400" style={{ width: `${comp.score}%` }} />
                  </div>
                  <span className="text-sm font-bold text-white">{comp.score}</span>
                </div>
              </div>
            ))}
          </div>
        )}
        {recommendations?.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-white/50 uppercase tracking-wider">Recommendations</div>
            {recommendations.map((rec, i) => (
              <div key={i} className="rounded-xl bg-white/5 border border-white/10 p-3 text-sm text-white/80">{rec}</div>
            ))}
          </div>
        )}
      </div>
    );
  };

  const SwotAnalysis = ({ data }) => {
    if (!data?.data?.swot) return null;
    const { swot, strategic_priority } = data.data;
    const sections = [
      { key: "strengths", label: "Strengths", color: "text-green-400", bg: "from-green-500/20 to-emerald-500/10", icon: "💪" },
      { key: "weaknesses", label: "Weaknesses", color: "text-red-400", bg: "from-red-500/20 to-rose-500/10", icon: "⚠️" },
      { key: "opportunities", label: "Opportunities", color: "text-blue-400", bg: "from-blue-500/20 to-cyan-500/10", icon: "🎯" },
      { key: "threats", label: "Threats", color: "text-yellow-400", bg: "from-yellow-500/20 to-orange-500/10", icon: "🛡️" },
    ];
    return (
      <div className="space-y-4 mt-4">
        <div className="grid grid-cols-2 gap-3">
          {sections.map(s => (
            <div key={s.key} className={`rounded-xl bg-gradient-to-br ${s.bg} border border-white/10 p-4`}>
              <div className={`text-sm font-semibold ${s.color} mb-2`}>{s.icon} {s.label}</div>
              <ul className="space-y-1">
                {(swot[s.key] || []).map((item, i) => (
                  <li key={i} className="text-xs text-white/70 flex gap-1"><span>•</span>{item}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        {strategic_priority && (
          <div className="rounded-xl bg-primary/10 border border-primary/30 p-4">
            <div className="text-xs font-semibold text-primary mb-1">Strategic Priority</div>
            <div className="text-sm text-white/80">{strategic_priority}</div>
          </div>
        )}
      </div>
    );
  };

  const GrowthStrategies = ({ data }) => {
    if (!data?.data?.growth_strategies) return null;
    const { growth_strategies, "90_day_target": target } = data.data;
    return (
      <div className="space-y-3 mt-4">
        {growth_strategies?.map((s, i) => (
          <div key={i} className="rounded-xl bg-white/5 border border-white/10 p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="font-semibold text-white text-sm">{i + 1}. {s.strategy}</div>
              <Badge className="bg-primary/20 text-primary text-xs">{s.estimated_impact}</Badge>
            </div>
            <p className="text-xs text-white/60 mb-2">{s.description}</p>
            <div className="flex gap-2 flex-wrap">
              {s.actions?.map((a, j) => (
                <div key={j} className="text-xs bg-white/5 rounded px-2 py-1 text-white/50">→ {a}</div>
              ))}
            </div>
          </div>
        ))}
        {target && (
          <div className="rounded-xl bg-gradient-to-r from-primary/20 to-blue-500/10 border border-primary/30 p-4">
            <div className="text-xs font-semibold text-primary mb-2">90-Day Target</div>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div><div className="text-lg font-bold text-white">{target.revenue_increase}</div><div className="text-xs text-white/50">Revenue Increase</div></div>
              <div><div className="text-lg font-bold text-white">{target.new_clients}</div><div className="text-xs text-white/50">New Clients</div></div>
              <div><div className="text-xs text-white/70 mt-2">{target.focus}</div></div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const Diagnosis = ({ data }) => {
    if (!data?.data?.diagnosis) return null;
    const { diagnosis, action_plan, key_metrics } = data.data;
    const severityColor = diagnosis.severity === "critical" ? "text-red-400 bg-red-500/10" : diagnosis.severity === "moderate" ? "text-yellow-400 bg-yellow-500/10" : "text-green-400 bg-green-500/10";
    return (
      <div className="space-y-4 mt-4">
        <div className={`rounded-xl ${severityColor} border border-current/20 p-4`}>
          <div className="font-semibold mb-2 capitalize">Severity: {diagnosis.severity}</div>
          <div className="space-y-1">
            {diagnosis.root_causes?.map((c, i) => <div key={i} className="text-sm text-white/80">• {c}</div>)}
          </div>
        </div>
        {key_metrics && (
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(key_metrics).map(([k, v]) => (
              <div key={k} className="rounded-xl bg-white/5 border border-white/10 p-3 text-center">
                <div className="text-lg font-bold text-white">{typeof v === 'number' ? `₹${v.toLocaleString()}` : v}</div>
                <div className="text-xs text-white/50">{k.replace(/_/g, ' ')}</div>
              </div>
            ))}
          </div>
        )}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-white/50 uppercase tracking-wider">Action Plan</div>
          {action_plan?.map((a, i) => (
            <div key={i} className="rounded-xl bg-white/5 border border-white/10 p-3">
              <div className="flex items-center justify-between mb-1">
                <div className="text-sm font-semibold text-white">{a.action}</div>
                <Badge className="bg-blue-500/20 text-blue-300 text-xs">{a.timeline}</Badge>
              </div>
              <p className="text-xs text-white/60">{a.details}</p>
              <p className="text-xs text-primary mt-1">Impact: {a.expected_impact}</p>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const tools = [
    { key: "health", label: "Business Health Score", prompt: "Calculate my business health score", icon: <Activity className="h-5 w-5" />, color: "from-green-500 to-emerald-600", ResultComponent: HealthScore },
    { key: "swot", label: "SWOT Analysis", prompt: "Perform a SWOT analysis of my business", icon: <Brain className="h-5 w-5" />, color: "from-blue-500 to-cyan-600", ResultComponent: SwotAnalysis },
    { key: "growth", label: "Growth Strategy", prompt: "What are the best growth strategies for my business?", icon: <TrendingUp className="h-5 w-5" />, color: "from-purple-500 to-violet-600", ResultComponent: GrowthStrategies },
    { key: "diagnosis", label: "Problem Diagnosis", prompt: "Diagnose my business problems and provide solutions", icon: <Zap className="h-5 w-5" />, color: "from-orange-500 to-red-600", ResultComponent: Diagnosis },
  ];

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-slate-950 via-blue-950/20 to-slate-950 p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/30">
              <Brain className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white">Strategy Agent</h1>
            <Badge className="bg-blue-500/20 text-blue-300 border border-blue-500/30">Executive Intelligence</Badge>
          </div>
          <p className="text-white/50 text-sm ml-12">CEO/CFO-level strategic advisor powered by your real business data</p>
        </div>
      </div>

      {/* Tools Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tools.map(tool => (
          <Card key={tool.key} className="bg-white/5 border-white/10 hover:border-white/20 transition-all duration-300">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-xl bg-gradient-to-br ${tool.color} shadow-lg`}>
                    <div className="text-white">{tool.icon}</div>
                  </div>
                  <CardTitle className="text-white text-base">{tool.label}</CardTitle>
                </div>
                <Button
                  size="sm"
                  onClick={() => callAgent(tool.key, tool.prompt)}
                  disabled={loading[tool.key]}
                  className={`bg-gradient-to-r ${tool.color} text-white border-0 hover:opacity-90`}
                >
                  {loading[tool.key] ? <RefreshCw className="h-3 w-3 animate-spin" /> : "Run"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {results[tool.key] ? (
                <tool.ResultComponent data={results[tool.key]} />
              ) : (
                <div className="text-center py-8 text-white/30">
                  <tool.icon />
                  <p className="text-sm mt-2">Click Run to execute analysis</p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
