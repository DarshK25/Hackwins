import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Brain,
  Heart,
  Rocket,
  Cog,
  Activity,
  Zap,
  TrendingUp,
  UserX,
  Star,
  Users,
  Tag,
  MapPin,
  Bot,
  RefreshCw,
  BarChart3,
} from "lucide-react";
import { useOrganization, useAuth } from "@clerk/clerk-react";
import { toast } from "sonner";

const AI_GATEWAY_URL = ""; // Use Vite proxy via relative paths (/api/v1)

// ─── Strategy result components ───────────────────────────────────────────
const HEALTH_COLOR = (score) => score >= 75 ? "#4CBB17" : score >= 50 ? "#FFB300" : "#CD1C18";

function HealthScore({ data }) {
  if (!data?.data?.health_score) return null;
  const { health_score, status, components, recommendations } = data.data;
  const color = HEALTH_COLOR(health_score);
  return (
    <div className="space-y-4 mt-4">
      <p className="text-xs text-[#A0A0A0]">Canonical business health score (used across MoneyOps).</p>
      <div className="mo-card p-6 text-center" style={{ borderColor: `${color}40` }}>
        <div className="text-7xl font-black" style={{ color }}>{health_score}</div>
        <div className="text-[#A0A0A0] text-sm mt-1">Health Score / 100</div>
        <span className="inline-block mt-2 text-xs px-2.5 py-1 rounded-full border font-medium" style={{ color, borderColor: `${color}40`, backgroundColor: `${color}15` }}>
          {status?.toUpperCase()}
        </span>
      </div>
      {components && (
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(components).map(([key, comp]) => (
            <div key={key} className="mo-card p-3">
              <div className="text-xs text-[#A0A0A0] mb-1">{comp.label}</div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 rounded-full bg-[#2A2A2A]">
                  <div className="h-2 rounded-full bg-[#4CBB17]" style={{ width: `${comp.score}%` }} />
                </div>
                <span className="text-sm font-bold text-white">{comp.score}</span>
              </div>
            </div>
          ))}
        </div>
      )}
      {recommendations?.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider">Recommendations</div>
          {recommendations.map((rec, i) => (
            <div key={i} className="mo-card p-3 text-sm text-white">{rec}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function SwotAnalysis({ data }) {
  if (!data?.data?.swot) return null;
  const { swot, strategic_priority } = data.data;
  const sections = [
    { key: "strengths", label: "Strengths", color: "#4CBB17", borderColor: "#4CBB1740" },
    { key: "weaknesses", label: "Weaknesses", color: "#CD1C18", borderColor: "#CD1C1840" },
    { key: "opportunities", label: "Opportunities", color: "#60A5FA", borderColor: "#60A5FA40" },
    { key: "threats", label: "Threats", color: "#FFB300", borderColor: "#FFB30040" },
  ];
  return (
    <div className="space-y-4 mt-4">
      <div className="grid grid-cols-2 gap-3">
        {sections.map(s => (
          <div key={s.key} className="mo-card p-4" style={{ borderColor: s.borderColor }}>
            <div className="text-sm font-semibold mb-2" style={{ color: s.color }}>{s.label}</div>
            <ul className="space-y-1">
              {(swot[s.key] || []).map((item, i) => (
                <li key={i} className="text-xs text-[#A0A0A0] flex gap-1"><span>•</span>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      {strategic_priority && (
        <div className="mo-card p-4 border-[#4CBB1740]">
          <div className="text-xs font-semibold text-[#4CBB17] mb-1">Strategic Priority</div>
          <div className="text-sm text-[#A0A0A0]">{strategic_priority}</div>
        </div>
      )}
    </div>
  );
}

function GrowthStrategies({ data }) {
  if (!data?.data?.growth_strategies) return null;
  const { growth_strategies, "90_day_target": target } = data.data;
  return (
    <div className="space-y-3 mt-4">
      {growth_strategies?.map((s, i) => (
        <div key={i} className="mo-card p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold text-white text-sm">{i + 1}. {s.strategy}</div>
            <span className="text-xs px-2 py-0.5 rounded border border-[#4CBB1740] text-[#4CBB17]">{s.estimated_impact}</span>
          </div>
          <p className="text-xs text-[#A0A0A0] mb-2">{s.description}</p>
          <div className="flex gap-2 flex-wrap">
            {s.actions?.map((a, j) => (
              <div key={j} className="text-xs bg-[#2A2A2A] rounded px-2 py-1 text-[#A0A0A0]">→ {a}</div>
            ))}
          </div>
        </div>
      ))}
      {target && (
        <div className="mo-card p-4 border-[#4CBB1740]">
          <div className="text-xs font-semibold text-[#4CBB17] mb-2">90-Day Target</div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div><div className="text-lg font-bold text-white">{target.revenue_increase}</div><div className="text-xs text-[#A0A0A0]">Revenue Increase</div></div>
            <div><div className="text-lg font-bold text-white">{target.new_clients}</div><div className="text-xs text-[#A0A0A0]">New Clients</div></div>
            <div><div className="text-xs text-[#A0A0A0] mt-2">{target.focus}</div></div>
          </div>
        </div>
      )}
    </div>
  );
}

function Diagnosis({ data }) {
  if (!data?.data?.diagnosis) return null;
  const { diagnosis, action_plan, key_metrics } = data.data;
  const severityStyle = diagnosis.severity === "critical" ? { color: "#CD1C18", borderColor: "#CD1C1840", backgroundColor: "#CD1C1810" } : diagnosis.severity === "moderate" ? { color: "#FFB300", borderColor: "#FFB30040", backgroundColor: "#FFB30010" } : { color: "#4CBB17", borderColor: "#4CBB1740", backgroundColor: "#4CBB1710" };
  return (
    <div className="space-y-4 mt-4">
      <div className="mo-card p-4" style={severityStyle}>
        <div className="font-semibold mb-2 capitalize">Severity: {diagnosis.severity}</div>
        <div className="space-y-1">
          {diagnosis.root_causes?.map((c, i) => <div key={i} className="text-sm text-[#A0A0A0]">• {c}</div>)}
        </div>
      </div>
      {key_metrics && (
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(key_metrics).map(([k, v]) => (
            <div key={k} className="mo-card p-3 text-center">
              <div className="text-lg font-bold text-white">{typeof v === "number" ? `₹${v.toLocaleString()}` : v}</div>
              <div className="text-xs text-[#A0A0A0]">{k.replace(/_/g, " ")}</div>
            </div>
          ))}
        </div>
      )}
      <div className="space-y-2">
        <div className="text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider">Action Plan</div>
        {action_plan?.map((a, i) => (
          <div key={i} className="mo-card p-3">
            <div className="flex items-center justify-between mb-1">
              <div className="text-sm font-semibold text-white">{a.action}</div>
              <span className="text-xs px-2 py-0.5 rounded border border-[#60A5FA40] text-[#60A5FA]">{a.timeline}</span>
            </div>
            <p className="text-xs text-[#A0A0A0]">{a.details}</p>
            <p className="text-xs text-[#4CBB17] mt-1">Impact: {a.expected_impact}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Customer result components ─────────────────────────────────────────────
function ChurnResult({ data }) {
  if (!data?.data) return null;
  const { churn_risk_summary, at_risk_clients } = data.data;
  const riskItems = [
    { label: "High Risk", value: churn_risk_summary?.high_risk, color: "#CD1C18" },
    { label: "Medium Risk", value: churn_risk_summary?.medium_risk, color: "#FFB300" },
    { label: "Low Risk", value: churn_risk_summary?.low_risk, color: "#4CBB17" },
  ];
  return (
    <div className="space-y-3 mt-3">
      {churn_risk_summary && (
        <div className="grid grid-cols-3 gap-2">
          {riskItems.map(item => (
            <div key={item.label} className="mo-card text-center p-3">
              <div className="text-2xl font-bold" style={{ color: item.color }}>{item.value}</div>
              <div className="text-xs text-[#A0A0A0]">{item.label}</div>
            </div>
          ))}
        </div>
      )}
      {at_risk_clients?.slice(0, 5).map((c, i) => (
        <div key={i} className="mo-card p-3">
          <div className="flex items-center justify-between mb-1">
            <div className="font-semibold text-white text-sm">{c.name}</div>
            <span className={`text-xs px-2 py-0.5 rounded border ${c.churn_risk === "high" ? "border-[#CD1C1840] text-[#CD1C18]" : "border-[#FFB30040] text-[#FFB300]"}`}>
              {c.churn_risk?.toUpperCase()} RISK
            </span>
          </div>
          <div className="text-xs text-[#A0A0A0] mb-2">{c.churn_reason}</div>
          <div className="text-xs text-[#4CBB17]">{c.intervention}</div>
        </div>
      ))}
    </div>
  );
}

function CLVResult({ data }) {
  if (!data?.data) return null;
  const { total_portfolio_value, clients } = data.data;
  return (
    <div className="space-y-3 mt-3">
      {total_portfolio_value != null && (
        <div className="mo-card p-4 text-center border-[#A78BFA40]">
          <div className="text-3xl font-black text-white">₹{Number(total_portfolio_value).toLocaleString()}</div>
          <div className="text-xs text-[#A0A0A0] mt-1">Total Portfolio CLV</div>
        </div>
      )}
      {clients?.slice(0, 5).map((c, i) => (
        <div key={i} className="mo-card p-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-semibold text-white text-sm">{c.name}</div>
              <div className="text-xs text-[#A0A0A0]">{c.segment}</div>
            </div>
            <div className="text-right">
              <div className="text-sm font-bold text-[#4CBB17]">₹{c.clv?.toLocaleString()}</div>
              <div className="text-xs text-[#A0A0A0]">CLV</div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

const SEGMENT_BORDER = { Champions: "#4CBB1740", "Loyal Customers": "#60A5FA40", "At Risk": "#CD1C1840", "Lost Customers": "#2A2A2A" };

function SegmentResult({ data }) {
  if (!data?.data?.segments) return null;
  const { segments } = data.data;
  return (
    <div className="space-y-3 mt-3">
      {segments?.map((seg, i) => (
        <div key={i} className="mo-card p-4" style={{ borderColor: SEGMENT_BORDER[seg.segment] || "#2A2A2A" }}>
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold text-sm text-white">{seg.segment}</div>
            <span className="text-xs text-[#A0A0A0]">{seg.count} clients</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs text-[#A0A0A0]">
            <div>Revenue: ₹{seg.total_revenue?.toLocaleString()}</div>
            <div>Avg: ₹{seg.avg_value?.toLocaleString()}</div>
          </div>
          <div className="text-xs text-[#A0A0A0] mt-2">{seg.action}</div>
        </div>
      ))}
    </div>
  );
}

// ─── Growth result components ───────────────────────────────────────────────
function PricingResult({ data }) {
  if (!data?.data) return null;
  const { current_avg_price, recommended_price, pricing_tiers, justification } = data.data;
  return (
    <div className="space-y-3 mt-3">
      {current_avg_price != null && recommended_price != null && (
        <div className="grid grid-cols-2 gap-3">
          <div className="mo-card p-3 text-center">
            <div className="text-2xl font-bold text-white">₹{Number(current_avg_price).toLocaleString()}</div>
            <div className="text-xs text-[#A0A0A0]">Current Avg Price</div>
          </div>
          <div className="mo-card p-3 text-center border-[#4CBB1740]">
            <div className="text-2xl font-bold text-[#4CBB17]">₹{Number(recommended_price).toLocaleString()}</div>
            <div className="text-xs text-[#A0A0A0]">Recommended Price</div>
          </div>
        </div>
      )}
      {pricing_tiers?.map((tier, i) => (
        <div key={i} className="mo-card p-3">
          <div className="flex items-center justify-between mb-1">
            <div className="font-semibold text-white text-sm">{tier.tier}</div>
            <div className="font-bold text-[#4CBB17]">₹{tier.price?.toLocaleString()}</div>
          </div>
          <p className="text-xs text-[#A0A0A0] mb-1">{tier.description}</p>
          <div className="text-xs text-[#4CBB17]">{tier.projected_revenue}</div>
        </div>
      ))}
      {justification && (
        <div className="mo-card p-3 text-xs text-[#A0A0A0]">{justification}</div>
      )}
    </div>
  );
}

function ExpansionResult({ data }) {
  if (!data?.data?.opportunities) return null;
  const { opportunities, total_addressable_market } = data.data;
  return (
    <div className="space-y-3 mt-3">
      {total_addressable_market && (
        <div className="mo-card p-4 text-center border-[#60A5FA40]">
          <div className="text-2xl font-bold text-white">{total_addressable_market}</div>
          <div className="text-xs text-[#A0A0A0]">Total Addressable Market</div>
        </div>
      )}
      {opportunities?.map((opp, i) => (
        <div key={i} className="mo-card p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold text-white text-sm">{opp.market}</div>
            <span className="text-xs text-[#60A5FA]">{opp.estimated_revenue}</span>
          </div>
          <div className="flex gap-2 mb-2">
            <span className={`text-xs px-2 py-0.5 rounded border ${opp.difficulty === "Low" ? "border-[#4CBB1740] text-[#4CBB17]" : opp.difficulty === "Medium" ? "border-[#FFB30040] text-[#FFB300]" : "border-[#CD1C1840] text-[#CD1C18]"}`}>
              {opp.difficulty} Difficulty
            </span>
            <span className="text-xs text-[#A0A0A0]">{opp.timeframe}</span>
          </div>
          <ul className="space-y-1">
            {opp.steps?.map((s, j) => <li key={j} className="text-xs text-[#A0A0A0]">→ {s}</li>)}
          </ul>
        </div>
      ))}
    </div>
  );
}

// ─── Operations result components ────────────────────────────────────────────
function EfficiencyResult({ data }) {
  if (!data?.data) return null;
  const { efficiency_score, bottlenecks, quick_wins } = data.data;
  return (
    <div className="space-y-3 mt-3">
      {efficiency_score !== undefined && (
        <div className="mo-card p-4 text-center border-[#FFB30040]">
          <div className="text-5xl font-black text-[#FFB300]">{efficiency_score}</div>
          <div className="text-xs text-[#A0A0A0] mt-1">Efficiency Score / 100</div>
        </div>
      )}
      {bottlenecks?.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-[#A0A0A0] uppercase">Bottlenecks</div>
          {bottlenecks.map((b, i) => (
            <div key={i} className="mo-card p-3 border-[#CD1C1840]">
              <div className="font-semibold text-[#CD1C18] text-sm mb-1">{b.issue}</div>
              <div className="text-xs text-[#A0A0A0] mb-1">{b.impact}</div>
              <div className="text-xs text-[#4CBB17]">{b.solution}</div>
            </div>
          ))}
        </div>
      )}
      {quick_wins?.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-semibold text-[#A0A0A0] uppercase">Quick Wins</div>
          {quick_wins.map((w, i) => (
            <div key={i} className="mo-card p-3 border-[#4CBB1740]">
              <div className="flex justify-between mb-1">
                <div className="font-semibold text-[#4CBB17] text-sm">{w.action}</div>
                <span className="text-xs text-[#4CBB17]">{w.timeframe}</span>
              </div>
              <div className="text-xs text-[#A0A0A0]">{w.impact}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AutomationResult({ data }) {
  if (!data?.data?.automation_opportunities) return null;
  const { automation_opportunities, estimated_savings } = data.data;
  return (
    <div className="space-y-3 mt-3">
      {estimated_savings && (
        <div className="mo-card p-4 border-[#60A5FA40]">
          <div className="text-center mb-2">
            <div className="text-2xl font-bold text-[#60A5FA]">{estimated_savings.hours_saved_monthly} hrs/mo</div>
            <div className="text-xs text-[#A0A0A0]">Time Saved</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-[#4CBB17]">₹{estimated_savings.cost_saved_monthly?.toLocaleString()}/mo</div>
            <div className="text-xs text-[#A0A0A0]">Cost Saved</div>
          </div>
        </div>
      )}
      {automation_opportunities?.map((opp, i) => (
        <div key={i} className="mo-card p-3">
          <div className="flex items-center justify-between mb-1">
            <div className="font-semibold text-white text-sm">{opp.process}</div>
            <span className="text-xs text-[#60A5FA]">{opp.priority}</span>
          </div>
          <div className="text-xs text-[#A0A0A0] mb-1">{opp.time_saved_hours}h/mo saved</div>
          <div className="text-xs text-[#4CBB17]">{opp.tool_recommendation}</div>
        </div>
      ))}
    </div>
  );
}

// ─── Tab config: agentKey, label, icon, tools[] ──────────────────────────────
const STRATEGY_TOOLS = [
  { key: "health", label: "Business Health Score", prompt: "Calculate my business health score", icon: <Activity className="h-5 w-5" />, color: "from-green-500 to-emerald-600", ResultComponent: HealthScore },
  { key: "swot", label: "SWOT Analysis", prompt: "Perform a SWOT analysis of my business", icon: <Brain className="h-5 w-5" />, color: "from-blue-500 to-cyan-600", ResultComponent: SwotAnalysis },
  { key: "growth", label: "Growth Strategy", prompt: "What are the best growth strategies for my business?", icon: <TrendingUp className="h-5 w-5" />, color: "from-purple-500 to-violet-600", ResultComponent: GrowthStrategies },
  { key: "diagnosis", label: "Problem Diagnosis", prompt: "Diagnose my business problems and provide solutions", icon: <Zap className="h-5 w-5" />, color: "from-orange-500 to-red-600", ResultComponent: Diagnosis },
];

const CUSTOMER_TOOLS = [
  { key: "churn", label: "Churn Prediction", prompt: "Predict customer churn risk", icon: <UserX className="h-5 w-5" />, color: "from-red-500 to-rose-600", ResultComponent: ChurnResult },
  { key: "clv", label: "Customer Lifetime Value", prompt: "Calculate customer lifetime value", icon: <Star className="h-5 w-5" />, color: "from-purple-500 to-violet-600", ResultComponent: CLVResult },
  { key: "segment", label: "Customer Segmentation", prompt: "Segment my customers by value", icon: <Users className="h-5 w-5" />, color: "from-blue-500 to-cyan-600", ResultComponent: SegmentResult },
];

const GROWTH_TOOLS = [
  { key: "pricing", label: "Pricing Optimization", prompt: "Optimize my pricing strategy", icon: <Tag className="h-5 w-5" />, color: "from-green-500 to-emerald-600", ResultComponent: PricingResult },
  { key: "expansion", label: "Market Expansion", prompt: "Identify market expansion opportunities", icon: <MapPin className="h-5 w-5" />, color: "from-blue-500 to-cyan-600", ResultComponent: ExpansionResult },
];

const OPERATIONS_TOOLS = [
  { key: "efficiency", label: "Efficiency Analysis", prompt: "Analyze my business process efficiency", icon: <Zap className="h-5 w-5" />, color: "from-orange-500 to-amber-600", ResultComponent: EfficiencyResult },
  { key: "automation", label: "Automation Opportunities", prompt: "Find automation opportunities in my operations", icon: <Bot className="h-5 w-5" />, color: "from-blue-500 to-cyan-600", ResultComponent: AutomationResult },
];

const TABS = [
  { id: "strategy", label: "Strategy", icon: Brain, tools: STRATEGY_TOOLS, sessionPrefix: "strategy" },
  { id: "customer", label: "Customer", icon: Heart, tools: CUSTOMER_TOOLS, sessionPrefix: "customer" },
  { id: "growth", label: "Growth", icon: Rocket, tools: GROWTH_TOOLS, sessionPrefix: "growth" },
  { id: "operations", label: "Operations", icon: Cog, tools: OPERATIONS_TOOLS, sessionPrefix: "ops" },
];

// ─── Shared card grid for one agent tab ────────────────────────────────────
function AgentToolsGrid({ agentKey, tools, loading, results, onRun }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {tools.map(tool => {
        const resultKey = `${agentKey}.${tool.key}`;
        const ResultComponent = tool.ResultComponent;
        const isLoading = loading[resultKey];
        const result = results[resultKey];
        return (
          <div key={tool.key} className="mo-card">
            <div className="flex items-center justify-between pb-3 border-b border-[#2A2A2A]">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-[#2A2A2A]" style={{ color: "#4CBB17" }}>
                  {tool.icon}
                </div>
                <h3 className="font-semibold text-white text-base">{tool.label}</h3>
              </div>
              <button
                type="button"
                onClick={() => onRun(agentKey, tool.key, tool.prompt)}
                disabled={isLoading}
                className="mo-btn-primary flex items-center gap-1.5 text-sm py-1.5 px-3 disabled:opacity-50"
              >
                {isLoading ? <RefreshCw className="h-3 w-3 animate-spin" /> : "Run"}
              </button>
            </div>
            <div className="pt-4">
              {result ? (
                <ResultComponent data={result} />
              ) : (
                <div className="text-center py-8 text-[#A0A0A0]">
                  {tool.icon}
                  <p className="text-sm mt-2">Click Run to execute analysis</p>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Mock data for testing ratios and layout (same shape as API responses)
const MOCK_RESULTS = {
  "strategy.health": {
    data: {
      health_score: 72,
      status: "good",
      components: { financial: { label: "Financial", score: 78 }, operational: { label: "Operational", score: 65 }, growth: { label: "Growth", score: 70 }, risk: { label: "Risk", score: 75 } },
      recommendations: ["Reduce overdue receivables", "Review fixed costs for Q3"],
    },
  },
  "strategy.swot": {
    data: {
      swot: {
        strengths: ["Strong client retention", "Healthy cash reserves"],
        weaknesses: ["Limited marketing spend", "Single revenue stream"],
        opportunities: ["Expand to adjacent verticals", "Upsell existing clients"],
        threats: ["Competitor pricing pressure", "Regulatory changes"],
      },
      strategic_priority: "Focus on retention and upsell before aggressive expansion.",
    },
  },
  "customer.churn": {
    data: {
      churn_risk_summary: { high_risk: 3, medium_risk: 7, low_risk: 24 },
      at_risk_clients: [
        { name: "Acme Corp", churn_risk: "high", churn_reason: "Declining engagement", intervention: "Schedule check-in call" },
        { name: "Beta Ltd", churn_risk: "medium", churn_reason: "Contract renewal in 60 days", intervention: "Send renewal proposal" },
      ],
    },
  },
  "customer.clv": {
    data: {
      total_portfolio_value: 2450000,
      clients: [
        { name: "Acme Corp", segment: "Enterprise", clv: 420000 },
        { name: "Beta Ltd", segment: "Mid-market", clv: 185000 },
      ],
    },
  },
  "growth.pricing": {
    data: {
      current_avg_price: 45000,
      recommended_price: 52000,
      pricing_tiers: [
        { tier: "Starter", price: 25000, description: "Basic plan", projected_revenue: "+12% adoption" },
        { tier: "Professional", price: 52000, description: "Recommended", projected_revenue: "+18% revenue" },
      ],
      justification: "Benchmark data supports 15% increase with minimal churn risk.",
    },
  },
  "operations.efficiency": {
    data: {
      efficiency_score: 68,
      bottlenecks: [
        { issue: "Manual invoice entry", impact: "8 hrs/week", solution: "Implement bulk import" },
      ],
      quick_wins: [
        { action: "Template library for proposals", timeframe: "1 week", impact: "Save 4 hrs/week" },
      ],
    },
  },
};

export default function BusinessAnalyticsPage() {
  const { organization } = useOrganization();
  const { getToken } = useAuth();
  const [loading, setLoading] = useState({});
  const [results, setResults] = useState(MOCK_RESULTS);

  const callAgent = async (agentKey, toolKey, prompt) => {
    const resultKey = `${agentKey}.${toolKey}`;
    const tab = TABS.find(t => t.id === agentKey);
    const sessionPrefix = tab?.sessionPrefix || agentKey;
    setLoading(prev => ({ ...prev, [resultKey]: true }));
    try {
      const token = await getToken();
      const res = await fetch(`${AI_GATEWAY_URL}/api/v1/voice/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify({
          text: prompt,
          user_id: "user",
          org_id: organization?.id || "default_org",
          session_id: `${sessionPrefix}-${Date.now()}`,
          context: {},
        }),
      });
      const data = await res.json();
      setResults(prev => ({ ...prev, [resultKey]: data }));
      toast.success("Analysis complete");
    } catch (err) {
      toast.error(`Failed: ${err.message}`);
    } finally {
      setLoading(prev => ({ ...prev, [resultKey]: false }));
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <div className="rounded-xl p-3" style={{ backgroundColor: "#4CBB1720", border: "1px solid #4CBB1740" }}>
          <BarChart3 className="h-6 w-6 text-[#4CBB17]" />
        </div>
        <h1 className="mo-h1">Business Analytics</h1>
      </div>

      <Tabs defaultValue="strategy" className="w-full">
        <TabsList className="bg-[#1A1A1A] border border-[#2A2A2A] p-1 rounded-xl w-fit flex gap-1">
          {TABS.map(tab => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              className="data-[state=active]:bg-[#4CBB1715] data-[state=active]:text-[#4CBB17] data-[state=active]:border-[#4CBB1740] rounded-lg px-4 py-2 text-[#A0A0A0] border border-transparent"
            >
              <tab.icon className="h-4 w-4 mr-2 inline" />
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {TABS.map(tab => (
          <TabsContent key={tab.id} value={tab.id} className="mt-6">
            <AgentToolsGrid
              agentKey={tab.id}
              tools={tab.tools}
              loading={loading}
              results={results}
              onRun={callAgent}
            />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
