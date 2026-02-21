import { useEffect, useState } from "react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
    GitMerge,
    Activity,
    MessageSquare,
    Clock,
    CheckCircle2,
    AlertCircle,
    Loader2,
    RefreshCw,
    Mic,
    Users,
    BarChart3,
    FileText,
    TrendingUp,
} from "lucide-react";

export function OrchestratorDashboard({ businessId }) {
    const [loading, setLoading] = useState(true);
    const [activities, setActivities] = useState([]);
    const [conversations, setConversations] = useState([]);
    const [agentStatuses, setAgentStatuses] = useState([
        {
            name: "Finance Agent",
            status: "active",
            lastActivity: new Date(),
            tasksCompleted: 12,
            currentTask: "Analyzing Q4 cash flow",
        },
        {
            name: "Sales Agent",
            status: "idle",
            lastActivity: new Date(),
            tasksCompleted: 8,
        },
        {
            name: "Research Agent",
            status: "processing",
            lastActivity: new Date(),
            tasksCompleted: 15,
            currentTask: "Market trend analysis",
        },
        {
            name: "Compliance Agent",
            status: "idle",
            lastActivity: new Date(),
            tasksCompleted: 5,
        },
    ]);

    useEffect(() => {
        fetchOrchestratorData();
        const interval = setInterval(fetchOrchestratorData, 10000);
        return () => clearInterval(interval);
    }, [businessId]);

    async function fetchOrchestratorData() {
        try {
            // Fetch activities
            const activitiesRes = await fetch(
                `/api/orchestrator/activities?businessId=${businessId}`
            );
            if (activitiesRes.ok) {
                const data = await activitiesRes.json();
                setActivities(data.activities || []);
            } else {
                // Fallback mock data
                setActivities([
                    {
                        id: "1",
                        timestamp: new Date(),
                        type: "task_assigned",
                        description: "Generated Q3 Financial Report",
                        status: "completed",
                        agent: "Finance Agent",
                    },
                    {
                        id: "2",
                        timestamp: new Date(Date.now() - 1000 * 60 * 5),
                        type: "decision_made",
                        description: "Approved invoice #INV-2024-001",
                        status: "completed",
                        agent: "Finance Agent",
                    },
                    {
                        id: "3",
                        timestamp: new Date(Date.now() - 1000 * 60 * 15),
                        type: "insight_generated",
                        description: "Identified potential cash flow risk",
                        status: "in_progress",
                        agent: "Research Agent",
                    },
                ]);
            }

            // Fetch voice conversations
            const conversationsRes = await fetch(
                `/api/orchestrator/conversations?businessId=${businessId}`
            );
            if (conversationsRes.ok) {
                const data = await conversationsRes.json();
                setConversations(data.conversations || []);
            } else {
                // Fallback mock data
                setConversations([
                    {
                        id: "vc-1",
                        startedAt: new Date(Date.now() - 1000 * 60 * 60 * 2),
                        duration: 120, // seconds
                        summary: "Discussed Q4 Sales Strategy",
                        status: "completed",
                        messages: [
                            {
                                role: "user",
                                content: "How are our sales looking for Q4?",
                                timestamp: new Date(),
                            },
                            {
                                role: "assistant",
                                content:
                                    "Sales are up 15% compared to Q3. Would you like a detailed breakdown?",
                                timestamp: new Date(),
                            },
                        ],
                        tasksGenerated: ["Generate Sales Report", "Email Team Lead"],
                    },
                ]);
            }
        } catch (error) {
            console.error("Failed to fetch orchestrator data:", error);
        } finally {
            setLoading(false);
        }
    }

    const getStatusColor = (status) => {
        switch (status) {
            case "completed":
                return "bg-green-500";
            case "in_progress":
            case "active":
            case "processing":
                return "bg-blue-500 animate-pulse";
            case "pending":
            case "idle":
                return "bg-gray-400";
            default:
                return "bg-gray-400";
        }
    };

    if (loading) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Loader2 className="h-5 w-5 animate-spin" />
                        Loading Orchestrator Dashboard...
                    </CardTitle>
                </CardHeader>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                        <GitMerge className="h-8 w-8 text-primary" />
                        🎯 Orchestrator Command Center
                    </h2>
                    <p className="text-muted-foreground">
                        Central intelligence coordinating all agents and operations
                    </p>
                </div>
                <Button variant="outline" size="sm" onClick={fetchOrchestratorData}>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                </Button>
            </div>

            {/* Overview Stats */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {agentStatuses.filter((a) => a.status !== "idle").length} /{" "}
                            {agentStatuses.length}
                        </div>
                        <p className="text-xs text-muted-foreground">Currently operational</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            Voice Calls Today
                        </CardTitle>
                        <Mic className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{conversations.length}</div>
                        <p className="text-xs text-muted-foreground">Total conversations</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Tasks Delegated</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {agentStatuses.reduce(
                                (sum, agent) => sum + agent.tasksCompleted,
                                0
                            )}
                        </div>
                        <p className="text-xs text-muted-foreground">This month</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Efficiency Score</CardTitle>
                        <TrendingUp className="h-4 w-4 text-green-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold text-green-600">94%</div>
                        <p className="text-xs text-muted-foreground">+12% from last week</p>
                    </CardContent>
                </Card>
            </div>

            {/* Main Tabs */}
            <Tabs defaultValue="activities" className="space-y-4">
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="activities">Live Activities</TabsTrigger>
                    <TabsTrigger value="conversations">Voice Call History</TabsTrigger>
                    <TabsTrigger value="agents">Agent Network</TabsTrigger>
                </TabsList>

                {/* Activities Tab */}
                <TabsContent value="activities">
                    <Card>
                        <CardHeader>
                            <CardTitle>🔴 Real-Time Orchestration Activities</CardTitle>
                            <CardDescription>
                                Live feed of all orchestrator decisions and actions
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[500px]">
                                <div className="space-y-3">
                                    {activities.length === 0 ? (
                                        <div className="text-center py-12 text-muted-foreground">
                                            <Activity className="h-12 w-12 mx-auto mb-3 opacity-20" />
                                            <p>
                                                No recent activities. Waiting for user interactions...
                                            </p>
                                        </div>
                                    ) : (
                                        activities.map((activity) => (
                                            <div
                                                key={activity.id}
                                                className="flex gap-3 p-3 border rounded-lg hover:bg-muted/50"
                                            >
                                                <div
                                                    className={`mt-1 h-2 w-2 rounded-full ${getStatusColor(
                                                        activity.status
                                                    )}`}
                                                />
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="font-semibold">
                                                            {activity.description}
                                                        </span>
                                                        {activity.agent && (
                                                            <Badge variant="outline">{activity.agent}</Badge>
                                                        )}
                                                    </div>
                                                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                                                        <Clock className="h-3 w-3" />
                                                        {new Date(activity.timestamp).toLocaleString()}
                                                    </p>
                                                </div>
                                                {activity.status === "completed" && (
                                                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                                                )}
                                                {activity.status === "in_progress" && (
                                                    <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
                                                )}
                                            </div>
                                        ))
                                    )}
                                </div>
                            </ScrollArea>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Conversations Tab */}
                <TabsContent value="conversations">
                    <Card>
                        <CardHeader>
                            <CardTitle>🎙️ Voice Call Conversation Threads</CardTitle>
                            <CardDescription>
                                Complete history of all voice interactions with the orchestrator
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[500px]">
                                <div className="space-y-4">
                                    {conversations.length === 0 ? (
                                        <div className="text-center py-12 text-muted-foreground">
                                            <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-20" />
                                            <p>No voice conversations yet.</p>
                                            <p className="text-sm">
                                                Click the voice button to start your first conversation!
                                            </p>
                                        </div>
                                    ) : (
                                        conversations.map((conv) => (
                                            <Card key={conv.id} className="border-2">
                                                <CardHeader>
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center gap-2">
                                                            <Mic className="h-5 w-5 text-primary" />
                                                            <CardTitle className="text-base">
                                                                {conv.summary || "Voice Conversation"}
                                                            </CardTitle>
                                                        </div>
                                                        <Badge
                                                            variant={
                                                                conv.status === "active" ? "default" : "secondary"
                                                            }
                                                        >
                                                            {conv.status}
                                                        </Badge>
                                                    </div>
                                                    <CardDescription className="flex items-center gap-3 mt-2">
                                                        <span>
                                                            {new Date(conv.startedAt).toLocaleString()}
                                                        </span>
                                                        {conv.duration && (
                                                            <span>
                                                                Duration: {Math.round(conv.duration / 60)}min
                                                            </span>
                                                        )}
                                                    </CardDescription>
                                                </CardHeader>
                                                <CardContent>
                                                    <div className="space-y-2 mb-3">
                                                        {conv.messages.slice(0, 3).map((msg, idx) => (
                                                            <div
                                                                key={idx}
                                                                className={`p-2 rounded-lg text-sm ${msg.role === "user"
                                                                        ? "bg-primary/10 ml-8"
                                                                        : "bg-muted mr-8"
                                                                    }`}
                                                            >
                                                                <div className="font-semibold text-xs mb-1">
                                                                    {msg.role === "user" ? "👤 You" : "🤖 Orchestrator"}
                                                                </div>
                                                                <div>{msg.content}</div>
                                                            </div>
                                                        ))}
                                                    </div>
                                                    {conv.tasksGenerated && conv.tasksGenerated.length > 0 && (
                                                        <>
                                                            <Separator className="my-3" />
                                                            <div>
                                                                <div className="text-sm font-semibold mb-2">
                                                                    ✅ Tasks Generated:
                                                                </div>
                                                                <ul className="text-sm space-y-1">
                                                                    {conv.tasksGenerated.map((task, idx) => (
                                                                        <li
                                                                            key={idx}
                                                                            className="flex items-start gap-2"
                                                                        >
                                                                            <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5" />
                                                                            {task}
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        </>
                                                    )}
                                                    <Button variant="outline" size="sm" className="mt-3">
                                                        View Full Transcript
                                                    </Button>
                                                </CardContent>
                                            </Card>
                                        ))
                                    )}
                                </div>
                            </ScrollArea>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Agent Network Tab */}
                <TabsContent value="agents">
                    <div className="grid gap-4 md:grid-cols-2">
                        {agentStatuses.map((agent) => (
                            <Card key={agent.name}>
                                <CardHeader>
                                    <div className="flex items-center justify-between">
                                        <CardTitle className="text-lg">{agent.name}</CardTitle>
                                        <div
                                            className={`h-3 w-3 rounded-full ${getStatusColor(
                                                agent.status
                                            )}`}
                                        />
                                    </div>
                                    <Badge
                                        variant={agent.status === "idle" ? "secondary" : "default"}
                                        className="w-fit"
                                    >
                                        {agent.status}
                                    </Badge>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <div className="flex justify-between text-sm">
                                        <span className="text-muted-foreground">
                                            Tasks Completed:
                                        </span>
                                        <span className="font-semibold">
                                            {agent.tasksCompleted}
                                        </span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-muted-foreground">Last Activity:</span>
                                        <span className="font-semibold">
                                            {agent.lastActivity.toLocaleTimeString()}
                                        </span>
                                    </div>
                                    {agent.currentTask && (
                                        <div className="bg-muted p-2 rounded text-sm">
                                            <div className="text-xs text-muted-foreground mb-1">
                                                Current Task:
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <Loader2 className="h-3 w-3 animate-spin" />
                                                {agent.currentTask}
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
}
