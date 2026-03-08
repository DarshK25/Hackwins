import { useEffect, useState } from "react";
import {
    GitMerge, Activity, MessageSquare, Clock, CheckCircle2,
    Loader2, RefreshCw, Mic, Users, TrendingUp,
} from "lucide-react";
import { useAuth, useUser } from "@clerk/clerk-react";

const STATUS_DOT = {
    completed: "#4CBB17",
    active: "#60A5FA",
    processing: "#60A5FA",
    in_progress: "#60A5FA",
    idle: "#3A3A3A",
    pending: "#3A3A3A",
};

const AGENT_STATUS_BADGE = {
    active: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
    processing: "bg-[#60A5FA20] text-[#60A5FA] border-[#60A5FA40]",
    idle: "bg-[#3A3A3A] text-[#A0A0A0] border-[#3A3A3A]",
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

export function OrchestratorDashboard({ businessId }) {
    const { getToken } = useAuth();
    const { user } = useUser();
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState("activities");
    const [activities, setActivities] = useState([]);
    const [conversations, setConversations] = useState([]);
    const [agentStatuses] = useState([
        { name: "Finance Agent", status: "active", lastActivity: new Date(), tasksCompleted: 12, currentTask: "Analyzing Q4 cash flow" },
        { name: "Sales Agent", status: "idle", lastActivity: new Date(), tasksCompleted: 8 },
        { name: "Research Agent", status: "processing", lastActivity: new Date(), tasksCompleted: 15, currentTask: "Market trend analysis" },
        { name: "Compliance Agent", status: "idle", lastActivity: new Date(), tasksCompleted: 5 },
    ]);

    useEffect(() => {
        if (businessId && user?.id) {
            fetchOrchestratorData();
            const interval = setInterval(fetchOrchestratorData, 10000);
            return () => clearInterval(interval);
        }
    }, [businessId, user?.id]);

    async function fetchOrchestratorData() {
        try {
            const token = await getToken();
            const [activitiesRes, conversationsRes] = await Promise.all([
                fetch(`/api/orchestrator/activities?businessId=${businessId}`, {
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "X-User-Id": user?.id
                    }
                }),
                fetch(`/api/orchestrator/conversations?businessId=${businessId}`, {
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "X-User-Id": user?.id
                    }
                }),
            ]);
            if (activitiesRes.ok) { const d = await activitiesRes.json(); setActivities(d.activities || []); }
            else setActivities([
                { id: "1", timestamp: new Date(), type: "task_assigned", description: "Generated Q3 Financial Report", status: "completed", agent: "Finance Agent" },
                { id: "2", timestamp: new Date(Date.now() - 300000), type: "decision_made", description: "Approved invoice #INV-2024-001", status: "completed", agent: "Finance Agent" },
                { id: "3", timestamp: new Date(Date.now() - 900000), type: "insight_generated", description: "Identified potential cash flow risk", status: "in_progress", agent: "Research Agent" },
            ]);
            if (conversationsRes.ok) { const d = await conversationsRes.json(); setConversations(d.conversations || []); }
            else setConversations([{
                id: "vc-1", startedAt: new Date(Date.now() - 7200000), duration: 120, summary: "Discussed Q4 Sales Strategy", status: "completed",
                messages: [{ role: "user", content: "How are our sales looking for Q4?", timestamp: new Date() }, { role: "assistant", content: "Sales are up 15% compared to Q3. Would you like a detailed breakdown?", timestamp: new Date() }],
                tasksGenerated: ["Generate Sales Report", "Email Team Lead"],
            }]);
        } catch (e) { console.error(e); }
        finally { setLoading(false); }
    }

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
            </div>
        );
    }

    const tabs = [
        { id: "activities", label: "Live Activities" },
        { id: "conversations", label: "Voice History" },
        { id: "agents", label: "Agent Network" },
    ];

    return (
        <div className="flex flex-col gap-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-4">
                    <div className="rounded-xl p-3" style={{ backgroundColor: "#60A5FA20", border: "1px solid #60A5FA40" }}>
                        <GitMerge className="h-6 w-6 text-[#60A5FA]" />
                    </div>
                    <div>
                        <h1 className="mo-h1">Orchestrator Command Center</h1>
                        <p className="mo-text-secondary mt-0.5">Central intelligence coordinating all agents and operations</p>
                    </div>
                </div>
                <button onClick={fetchOrchestratorData} className="mo-btn-secondary flex items-center gap-2 text-sm">
                    <RefreshCw className="h-4 w-4" /> Refresh
                </button>
            </div>

            {/* Stats */}
            <div className="grid gap-4 md:grid-cols-4">
                <StatCard label="Active Agents" value={`${agentStatuses.filter(a => a.status !== "idle").length} / ${agentStatuses.length}`} sub="Currently operational" icon={Users} iconColor="#60A5FA" />
                <StatCard label="Voice Calls Today" value={conversations.length} sub="Total conversations" icon={Mic} iconColor="#4CBB17" />
                <StatCard label="Tasks Delegated" value={agentStatuses.reduce((s, a) => s + a.tasksCompleted, 0)} sub="This month" icon={Activity} iconColor="#FFB300" />
                <StatCard label="Efficiency Score" value="94%" sub="+12% from last week" icon={TrendingUp} iconColor="#4CBB17" />
            </div>

            {/* Tabs */}
            <div className="mo-card !p-0">
                <div className="flex border-b border-[#2A2A2A] px-4">
                    {tabs.map(t => (
                        <button
                            key={t.id}
                            onClick={() => setActiveTab(t.id)}
                            className={`px-4 py-3.5 text-sm font-medium border-b-2 transition-colors ${activeTab === t.id ? "border-[#4CBB17] text-[#4CBB17]" : "border-transparent text-[#A0A0A0] hover:text-white"}`}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
                <div className="p-5">
                    {/* Activities */}
                    {activeTab === "activities" && (
                        <div className="flex flex-col gap-3">
                            <p className="text-xs text-[#A0A0A0] mb-1">Live feed of all orchestrator decisions and actions</p>
                            {activities.length === 0 ? (
                                <div className="flex flex-col items-center py-16 text-center">
                                    <Activity className="h-10 w-10 text-[#2A2A2A] mb-3" />
                                    <p className="text-[#A0A0A0] text-sm">No recent activities. Waiting for user interactions...</p>
                                </div>
                            ) : activities.map(a => (
                                <div key={a.id} className="flex gap-3 p-3 rounded-xl border border-[#2A2A2A] hover:border-[#3A3A3A] transition-all">
                                    <div className="mt-1.5 h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: STATUS_DOT[a.status] || "#3A3A3A" }} />
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <span className="font-semibold text-white text-sm">{a.description}</span>
                                            {a.agent && <span className="text-xs px-2 py-0.5 rounded-md bg-[#60A5FA20] text-[#60A5FA] border border-[#60A5FA40]">{a.agent}</span>}
                                        </div>
                                        <p className="text-xs text-[#A0A0A0] flex items-center gap-1 mt-1">
                                            <Clock className="h-3 w-3" /> {new Date(a.timestamp).toLocaleString()}
                                        </p>
                                    </div>
                                    {a.status === "completed" && <CheckCircle2 className="h-5 w-5 text-[#4CBB17] flex-shrink-0" />}
                                    {(a.status === "in_progress" || a.status === "processing") && <Loader2 className="h-5 w-5 text-[#60A5FA] animate-spin flex-shrink-0" />}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Conversations */}
                    {activeTab === "conversations" && (
                        <div className="flex flex-col gap-4">
                            <p className="text-xs text-[#A0A0A0] mb-1">Complete history of all voice interactions</p>
                            {conversations.length === 0 ? (
                                <div className="flex flex-col items-center py-16 text-center">
                                    <MessageSquare className="h-10 w-10 text-[#2A2A2A] mb-3" />
                                    <p className="text-[#A0A0A0] text-sm">No voice conversations yet.</p>
                                    <p className="text-xs text-[#A0A0A0] mt-1">Click the voice button to start your first conversation!</p>
                                </div>
                            ) : conversations.map(conv => (
                                <div key={conv.id} className="rounded-xl border border-[#2A2A2A] overflow-hidden">
                                    <div className="flex items-center justify-between p-4 border-b border-[#2A2A2A]">
                                        <div className="flex items-center gap-2">
                                            <Mic className="h-4 w-4 text-[#4CBB17]" />
                                            <span className="font-semibold text-white text-sm">{conv.summary || "Voice Conversation"}</span>
                                        </div>
                                        <span className={`text-xs px-2 py-0.5 rounded-full border ${conv.status === "active" ? "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]" : "bg-[#A0A0A020] text-[#A0A0A0] border-[#A0A0A040]"}`}>{conv.status}</span>
                                    </div>
                                    <div className="p-4 flex flex-col gap-2">
                                        <p className="text-xs text-[#A0A0A0] mb-1">{new Date(conv.startedAt).toLocaleString()}{conv.duration && ` · ${Math.round(conv.duration / 60)} min`}</p>
                                        {conv.messages.slice(0, 3).map((msg, idx) => (
                                            <div key={idx} className={`p-2.5 rounded-lg text-sm ${msg.role === "user" ? "bg-[#4CBB1715] ml-8 text-white" : "bg-[#1A1A1A] mr-8 text-[#A0A0A0]"}`}>
                                                <p className="text-xs font-semibold mb-1 text-[#A0A0A0]">{msg.role === "user" ? "You" : "Orchestrator"}</p>
                                                <p>{msg.content}</p>
                                            </div>
                                        ))}
                                        {conv.tasksGenerated?.length > 0 && (
                                            <div className="mt-2 pt-3 border-t border-[#2A2A2A]">
                                                <p className="text-xs font-semibold text-[#A0A0A0] mb-2">Tasks Generated:</p>
                                                <ul className="flex flex-col gap-1">
                                                    {conv.tasksGenerated.map((task, idx) => (
                                                        <li key={idx} className="flex items-center gap-2 text-sm text-white">
                                                            <CheckCircle2 className="h-3.5 w-3.5 text-[#4CBB17]" /> {task}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        <button className="mo-btn-secondary text-xs mt-2 self-start">View Full Transcript</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Agent Network */}
                    {activeTab === "agents" && (
                        <div className="grid gap-4 md:grid-cols-2">
                            {agentStatuses.map(agent => (
                                <div key={agent.name} className="rounded-xl border border-[#2A2A2A] p-4 hover:border-[#3A3A3A] transition-all">
                                    <div className="flex items-center justify-between mb-3">
                                        <h4 className="font-semibold text-white">{agent.name}</h4>
                                        <div className="flex items-center gap-2">
                                            <div className="h-2 w-2 rounded-full" style={{ backgroundColor: STATUS_DOT[agent.status] }} />
                                            <span className={`text-xs px-2 py-0.5 rounded-full border ${AGENT_STATUS_BADGE[agent.status] || AGENT_STATUS_BADGE.idle}`}>{agent.status}</span>
                                        </div>
                                    </div>
                                    <div className="flex flex-col gap-1.5 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-[#A0A0A0]">Tasks Completed</span>
                                            <span className="text-white font-semibold">{agent.tasksCompleted}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-[#A0A0A0]">Last Activity</span>
                                            <span className="text-white font-semibold">{agent.lastActivity.toLocaleTimeString()}</span>
                                        </div>
                                        {agent.currentTask && (
                                            <div className="mt-2 p-2.5 rounded-lg bg-[#1A1A1A] text-sm text-[#A0A0A0] flex items-center gap-2">
                                                <Loader2 className="h-3.5 w-3.5 text-[#60A5FA] animate-spin flex-shrink-0" />
                                                {agent.currentTask}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
