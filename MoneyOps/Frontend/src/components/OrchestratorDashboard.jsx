import { useEffect, useMemo, useState } from "react";
import { useAuth, useUser } from "@clerk/clerk-react";
import {
    Activity,
    AlertCircle,
    Bot,
    CircleDollarSign,
    Clock3,
    FileText,
    Filter,
    Loader2,
    MessageSquare,
    RefreshCw,
    UserRound,
    Users,
    X,
} from "lucide-react";
import { toast } from "sonner";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { formatAppDateTime } from "@/lib/dateTime";

const DEFAULT_AGENTS = ["Finance Agent", "Market Agent", "General Agent"];

const STATUS_STYLES = {
    COMPLETED: "border-[#4CBB1740] bg-[#4CBB1720] text-[#4CBB17]",
    FAILED: "border-[#F8717140] bg-[#F8717120] text-[#F87171]",
    PENDING: "border-[#FFB30040] bg-[#FFB30020] text-[#FFB300]",
    IN_PROGRESS: "border-[#60A5FA40] bg-[#60A5FA20] text-[#60A5FA]",
    PROCESSING: "border-[#60A5FA40] bg-[#60A5FA20] text-[#60A5FA]",
    ACTIVE: "border-[#60A5FA40] bg-[#60A5FA20] text-[#60A5FA]",
};

function formatDateTime(value) {
    if (!value) {
        return "--";
    }

    return formatAppDateTime(value, "en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function buildStableKey(prefix, ...parts) {
    const normalizedParts = parts
        .map((part) => (part == null ? "" : String(part).trim()))
        .filter(Boolean);

    return [prefix, ...normalizedParts].join("-");
}

function normalizeStatus(status) {
    return (status || "PENDING").toUpperCase();
}

function statusClassName(status) {
    return STATUS_STYLES[normalizeStatus(status)] || STATUS_STYLES.PENDING;
}

function getActivityIcon(type) {
    const normalizedType = (type || "").toUpperCase();

    if (normalizedType.includes("INVOICE")) {
        return FileText;
    }
    if (normalizedType.includes("CLIENT")) {
        return UserRound;
    }
    if (normalizedType.includes("PAYMENT")) {
        return CircleDollarSign;
    }
    if (normalizedType.includes("QUERY")) {
        return MessageSquare;
    }
    return Activity;
}

async function parseApiResponse(response, fallbackMessage) {
    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
        const payload = await response.json().catch(() => null);
        return payload?.message || payload?.error || payload?.data?.message || fallbackMessage;
    }

    const text = await response.text().catch(() => "");
    return text || fallbackMessage;
}

function DashboardSkeleton() {
    return (
        <div className="space-y-5">
            <div className="grid gap-4 md:grid-cols-4">
                {[1, 2, 3, 4].map((item) => (
                    <div key={item} className="mo-card animate-pulse">
                        <div className="h-4 w-24 rounded bg-[#202020]" />
                        <div className="mt-4 h-8 w-16 rounded bg-[#202020]" />
                        <div className="mt-3 h-3 w-28 rounded bg-[#202020]" />
                    </div>
                ))}
            </div>

            <div className="grid gap-5 xl:grid-cols-[420px_minmax(0,1fr)]">
                <div className="mo-card animate-pulse">
                    <div className="h-6 w-40 rounded bg-[#202020]" />
                    <div className="mt-5 space-y-3">
                        {[1, 2, 3].map((item) => (
                            <div key={item} className="h-24 rounded-xl bg-[#141414]" />
                        ))}
                    </div>
                </div>

                <div className="mo-card animate-pulse">
                    <div className="h-6 w-48 rounded bg-[#202020]" />
                    <div className="mt-5 space-y-3">
                        {[1, 2, 3, 4].map((item) => (
                            <div key={item} className="h-18 rounded-xl bg-[#141414]" />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

export function OrchestratorDashboard() {
    const { getToken } = useAuth();
    const { user } = useUser();
    const { loading: onboardingLoading, userId, orgId } = useOnboardingStatus();

    const [summary, setSummary] = useState(null);
    const [activitiesPage, setActivitiesPage] = useState({
        content: [],
        pageNumber: 0,
        totalPages: 0,
        totalElements: 0,
        first: true,
        last: true,
    });
    const [agentTasks, setAgentTasks] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [pageNumber, setPageNumber] = useState(0);
    const [agentFilter, setAgentFilter] = useState("ALL");
    const [statusFilter, setStatusFilter] = useState("ALL");
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [selectedSession, setSelectedSession] = useState(null);
    const [loadingSessionId, setLoadingSessionId] = useState(null);

    const hasContext = useMemo(() => Boolean(orgId && (userId || user?.id)), [orgId, userId, user?.id]);

    useEffect(() => {
        if (!onboardingLoading && hasContext) {
            loadDashboard(pageNumber);
        } else if (!onboardingLoading && !hasContext) {
            setLoading(false);
        }
    }, [onboardingLoading, hasContext, pageNumber]);

    async function buildHeaders(extra = {}) {
        const token = await getToken();
        return {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(userId || user?.id ? { "X-User-Id": userId || user?.id } : {}),
            ...(orgId ? { "X-Org-Id": orgId } : {}),
            ...extra,
        };
    }

    async function loadDashboard(page = 0) {
        if (!orgId) {
            setLoading(false);
            setError("Organization context is missing.");
            return;
        }

        try {
            setLoading(true);
            setError("");

            const headers = await buildHeaders();
            const activityQuery = new URLSearchParams({
                orgId,
                page: String(page),
                size: "20",
            });

            const [summaryResponse, activitiesResponse] = await Promise.all([
                fetch(`/api/orchestrator/summary?orgId=${encodeURIComponent(orgId)}`, { headers }),
                fetch(`/api/orchestrator/activities?${activityQuery.toString()}`, { headers }),
            ]);

            if (!summaryResponse.ok) {
                throw new Error(await parseApiResponse(summaryResponse, "Failed to load orchestrator summary"));
            }
            if (!activitiesResponse.ok) {
                throw new Error(await parseApiResponse(activitiesResponse, "Failed to load activities"));
            }

            const summaryPayload = await summaryResponse.json();
            const activitiesPayload = await activitiesResponse.json();
            const summaryData = summaryPayload?.data || null;
            const pageData = activitiesPayload?.data || {};

            setSummary(summaryData);
            setActivitiesPage({
                content: pageData.content || [],
                pageNumber: pageData.pageNumber || 0,
                totalPages: pageData.totalPages || 0,
                totalElements: pageData.totalElements || 0,
                first: pageData.first ?? true,
                last: pageData.last ?? true,
            });

            await loadAgentTasks(summaryData, headers);
        } catch (requestError) {
            console.error("Failed to load orchestrator dashboard", requestError);
            setSummary(null);
            setActivitiesPage({
                content: [],
                pageNumber: 0,
                totalPages: 0,
                totalElements: 0,
                first: true,
                last: true,
            });
            setAgentTasks({});
            setError(requestError.message || "Failed to load orchestrator dashboard");
        } finally {
            setLoading(false);
        }
    }

    async function loadAgentTasks(summaryData, headers) {
        const summaryAgents = (summaryData?.agentBreakdown || []).map((item) => item.agent);
        const agentNames = [...new Set([...DEFAULT_AGENTS, ...summaryAgents])];

        const responses = await Promise.all(
            agentNames.map(async (agent) => {
                const response = await fetch(
                    `/api/orchestrator/activities/agent/${encodeURIComponent(agent)}?orgId=${encodeURIComponent(orgId)}`,
                    { headers }
                );

                if (!response.ok) {
                    return [agent, []];
                }

                const payload = await response.json().catch(() => null);
                return [agent, Array.isArray(payload?.data) ? payload.data : []];
            })
        );

        setAgentTasks(Object.fromEntries(responses));
    }

    async function openSessionModal(sessionId) {
        if (!sessionId || !orgId) {
            return;
        }

        try {
            setLoadingSessionId(sessionId);
            const headers = await buildHeaders();
            const response = await fetch(
                `/api/orchestrator/activities/session/${encodeURIComponent(sessionId)}?orgId=${encodeURIComponent(orgId)}`,
                { headers }
            );

            if (!response.ok) {
                throw new Error(await parseApiResponse(response, "Failed to load session detail"));
            }

            const payload = await response.json();
            setSelectedSession(payload?.data || null);
        } catch (requestError) {
            console.error("Failed to load session detail", requestError);
            toast.error(requestError.message || "Failed to load session detail");
        } finally {
            setLoadingSessionId(null);
        }
    }

    const filteredActivities = useMemo(() => {
        return (activitiesPage.content || []).filter((activity) => {
            const matchesAgent = agentFilter === "ALL" || activity.agentName === agentFilter;
            const matchesStatus = statusFilter === "ALL" || normalizeStatus(activity.status) === statusFilter;

            const activityDate = activity.timestamp ? new Date(activity.timestamp) : null;
            const matchesStart =
                !startDate || !activityDate || activityDate >= new Date(`${startDate}T00:00:00`);
            const matchesEnd =
                !endDate || !activityDate || activityDate <= new Date(`${endDate}T23:59:59`);

            return matchesAgent && matchesStatus && matchesStart && matchesEnd;
        });
    }, [activitiesPage.content, agentFilter, statusFilter, startDate, endDate]);

    const agentCards = useMemo(() => {
        const breakdownMap = new Map((summary?.agentBreakdown || []).map((item) => [item.agent, item]));
        const agents = [...new Set([...DEFAULT_AGENTS, ...Object.keys(agentTasks)])];

        return agents.map((agentName) => {
            const breakdown = breakdownMap.get(agentName);
            const tasks = (agentTasks[agentName] || []).slice(0, 4);

            return {
                agentName,
                count: breakdown?.count || tasks.length,
                successRate: breakdown?.successRate || 0,
                tasks,
            };
        });
    }, [summary, agentTasks]);

    const filterAgentOptions = useMemo(() => {
        const agents = new Set(DEFAULT_AGENTS);
        (summary?.agentBreakdown || []).forEach((item) => agents.add(item.agent));
        return ["ALL", ...agents];
    }, [summary]);

    if (loading || onboardingLoading) {
        return <DashboardSkeleton />;
    }

    if (!hasContext) {
        return (
            <div className="mo-card rounded-2xl border border-dashed border-[#2A2A2A] bg-[#111111] px-6 py-10 text-center">
                <Bot className="mx-auto mb-4 h-12 w-12 text-[#2F2F2F]" />
                <div className="text-lg font-semibold text-white">Workspace context is not ready</div>
                <div className="mt-2 text-sm text-[#A0A0A0]">
                    The orchestrator dashboard will load once your organization context is available.
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="mo-card rounded-2xl border border-[#F8717140] bg-[#111111] px-6 py-10 text-center">
                <AlertCircle className="mx-auto mb-4 h-10 w-10 text-[#F87171]" />
                <div className="text-lg font-semibold text-white">Failed to load orchestrator activity</div>
                <div className="mt-2 text-sm text-[#A0A0A0]">{error}</div>
                <button onClick={() => loadDashboard(pageNumber)} className="mo-btn-primary mt-5">
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="mo-h1">Orchestrator Command Center</h1>
                    <p className="mo-text-secondary mt-1">
                        Track what each agent handled, how sessions progressed, and what finished successfully.
                    </p>
                </div>

                <button
                    onClick={() => loadDashboard(pageNumber)}
                    className="mo-btn-secondary flex items-center gap-2"
                >
                    <RefreshCw className="h-4 w-4" />
                    Refresh
                </button>
            </div>

            <div className="grid gap-4 md:grid-cols-4">
                <div className="mo-stat-card">
                    <div className="mb-2 flex items-center justify-between">
                        <div className="text-sm text-[#A0A0A0]">Total Tasks</div>
                        <Activity className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-3xl font-bold text-white">{summary?.totalTasks || 0}</div>
                </div>

                <div className="mo-stat-card">
                    <div className="mb-2 flex items-center justify-between">
                        <div className="text-sm text-[#A0A0A0]">Completed</div>
                        <Activity className="h-4 w-4 text-[#4CBB17]" />
                    </div>
                    <div className="text-3xl font-bold text-[#4CBB17]">{summary?.completedTasks || 0}</div>
                </div>

                <div className="mo-stat-card">
                    <div className="mb-2 flex items-center justify-between">
                        <div className="text-sm text-[#A0A0A0]">Failed</div>
                        <AlertCircle className="h-4 w-4 text-[#F87171]" />
                    </div>
                    <div className="text-3xl font-bold text-[#F87171]">{summary?.failedTasks || 0}</div>
                </div>

                <div className="mo-stat-card">
                    <div className="mb-2 flex items-center justify-between">
                        <div className="text-sm text-[#A0A0A0]">Pending</div>
                        <Clock3 className="h-4 w-4 text-[#FFB300]" />
                    </div>
                    <div className="text-3xl font-bold text-[#FFB300]">{summary?.pendingTasks || 0}</div>
                </div>
            </div>

            <div className="grid gap-5 xl:grid-cols-[420px_minmax(0,1fr)]">
                <div className="flex flex-col gap-5">
                    <div className="mo-card">
                        <div className="mb-4 flex items-center justify-between">
                            <div>
                                <h2 className="mo-h2">Agent Workload</h2>
                                <p className="mo-text-secondary mt-1">Recent tasks handled by each specialist agent.</p>
                            </div>
                            <Users className="h-5 w-5 text-[#A0A0A0]" />
                        </div>

                        <div className="space-y-4">
                            {agentCards.map((card) => (
                                <div key={card.agentName} className="rounded-2xl border border-[#232323] bg-[#111111] p-4">
                                    <div className="flex items-center justify-between gap-3">
                                        <div>
                                            <div className="font-semibold text-white">{card.agentName}</div>
                                            <div className="mt-1 text-xs text-[#A0A0A0]">
                                                {card.count} tasks handled
                                            </div>
                                        </div>
                                        <div className="rounded-full border border-[#2A2A2A] px-3 py-1 text-xs text-white">
                                            {card.successRate}% success
                                        </div>
                                    </div>

                                    <div className="mt-3 space-y-2">
                                        {card.tasks.length === 0 ? (
                                            <div className="text-sm text-[#666666]">No recent tasks for this agent.</div>
                                        ) : (
                                            card.tasks.map((task, index) => (
                                                <div key={buildStableKey("agent-task", task.id, task.timestamp, index)} className="rounded-xl border border-[#1D1D1D] bg-[#0C0C0C] px-3 py-2">
                                                    <div className="flex items-center justify-between gap-3">
                                                        <div className="text-sm text-white line-clamp-2">{task.description}</div>
                                                        <span className={`inline-flex rounded-md border px-2 py-1 text-[11px] font-semibold ${statusClassName(task.status)}`}>
                                                            {normalizeStatus(task.status)}
                                                        </span>
                                                    </div>
                                                    <div className="mt-2 text-xs text-[#A0A0A0]">
                                                        {formatDateTime(task.timestamp)}
                                                    </div>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="mo-card">
                        <div className="mb-4">
                            <h2 className="mo-h2">Recent Sessions</h2>
                            <p className="mo-text-secondary mt-1">Open a session to inspect the full conversation and actions.</p>
                        </div>

                        <div className="space-y-3">
                            {(summary?.recentSessions || []).length === 0 ? (
                                <div className="rounded-xl border border-dashed border-[#2A2A2A] px-4 py-8 text-center text-sm text-[#A0A0A0]">
                                    No recent sessions yet.
                                </div>
                            ) : (
                                (summary?.recentSessions || []).map((session, index) => (
                                    <button
                                        key={buildStableKey("session", session.sessionId, session.startedAt, index)}
                                        onClick={() => openSessionModal(session.sessionId)}
                                        className="w-full rounded-2xl border border-[#232323] bg-[#111111] px-4 py-3 text-left transition hover:border-[#3A3A3A]"
                                    >
                                        <div className="flex items-center justify-between gap-3">
                                            <div className="font-medium text-white">
                                                {session.summary || "Voice session"}
                                            </div>
                                            <span className={`inline-flex rounded-md border px-2 py-1 text-[11px] font-semibold ${statusClassName(session.status)}`}>
                                                {normalizeStatus(session.status)}
                                            </span>
                                        </div>
                                        <div className="mt-2 text-xs text-[#A0A0A0]">
                                            {session.sessionId} - {session.activityCount} activities - {formatDateTime(session.startedAt)}
                                        </div>
                                    </button>
                                ))
                            )}
                        </div>
                    </div>
                </div>

                <div className="mo-card">
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <h2 className="mo-h2">Activity Timeline</h2>
                            <p className="mo-text-secondary mt-1">Newest tasks first, with agent, status, and session context.</p>
                        </div>
                        <div className="text-sm text-[#A0A0A0]">
                            Showing {filteredActivities.length} of {activitiesPage.totalElements} activities
                        </div>
                    </div>

                    <div className="grid gap-3 rounded-2xl border border-[#202020] bg-[#111111] p-4 lg:grid-cols-4">
                        <div className="flex items-center gap-2">
                            <Filter className="h-4 w-4 text-[#A0A0A0]" />
                            <select
                                value={agentFilter}
                                onChange={(event) => setAgentFilter(event.target.value)}
                                className="w-full rounded-lg border border-[#2A2A2A] bg-[#0E0E0E] px-3 py-2 text-sm text-white outline-none"
                            >
                                {filterAgentOptions.map((agent) => (
                                    <option key={agent} value={agent}>
                                        {agent === "ALL" ? "All Agents" : agent}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <select
                            value={statusFilter}
                            onChange={(event) => setStatusFilter(event.target.value)}
                            className="rounded-lg border border-[#2A2A2A] bg-[#0E0E0E] px-3 py-2 text-sm text-white outline-none"
                        >
                            <option value="ALL">All Statuses</option>
                            <option value="COMPLETED">Completed</option>
                            <option value="FAILED">Failed</option>
                            <option value="PENDING">Pending</option>
                            <option value="IN_PROGRESS">In Progress</option>
                        </select>

                        <input
                            type="date"
                            value={startDate}
                            onChange={(event) => setStartDate(event.target.value)}
                            className="rounded-lg border border-[#2A2A2A] bg-[#0E0E0E] px-3 py-2 text-sm text-white outline-none"
                        />

                        <input
                            type="date"
                            value={endDate}
                            onChange={(event) => setEndDate(event.target.value)}
                            className="rounded-lg border border-[#2A2A2A] bg-[#0E0E0E] px-3 py-2 text-sm text-white outline-none"
                        />
                    </div>

                    <div className="mt-5 space-y-3">
                        {filteredActivities.length === 0 ? (
                            <div className="rounded-2xl border border-dashed border-[#2A2A2A] px-4 py-14 text-center">
                                <Activity className="mx-auto mb-4 h-10 w-10 text-[#2F2F2F]" />
                                <div className="text-sm text-[#A0A0A0]">
                                    No activities matched the current filters on this page.
                                </div>
                            </div>
                        ) : (
                            filteredActivities.map((activity, index) => {
                                const ActivityIcon = getActivityIcon(activity.type);

                                return (
                                    <div key={buildStableKey("timeline-activity", activity.id, activity.sessionId, activity.timestamp, index)} className="rounded-2xl border border-[#232323] bg-[#111111] p-4">
                                        <div className="flex items-start gap-3">
                                            <div className="rounded-xl border border-[#2A2A2A] bg-[#0D0D0D] p-2">
                                                <ActivityIcon className="h-4 w-4 text-[#A0A0A0]" />
                                            </div>

                                            <div className="min-w-0 flex-1">
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <div className="font-medium text-white">{activity.description}</div>
                                                    <span className="rounded-md border border-[#60A5FA40] bg-[#60A5FA20] px-2 py-1 text-[11px] font-semibold text-[#60A5FA]">
                                                        {activity.agentName}
                                                    </span>
                                                    <span className={`rounded-md border px-2 py-1 text-[11px] font-semibold ${statusClassName(activity.status)}`}>
                                                        {normalizeStatus(activity.status)}
                                                    </span>
                                                </div>

                                                <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-[#A0A0A0]">
                                                    <span>{activity.type}</span>
                                                    <span>{formatDateTime(activity.timestamp)}</span>
                                                    {activity.sessionId ? (
                                                        <button
                                                            onClick={() => openSessionModal(activity.sessionId)}
                                                            className="text-[#60A5FA] transition hover:text-[#93C5FD]"
                                                        >
                                                            Session {activity.sessionId}
                                                        </button>
                                                    ) : null}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>

                    <div className="mt-5 flex items-center justify-between gap-3">
                        <div className="text-sm text-[#A0A0A0]">
                            Page {activitiesPage.pageNumber + 1} of {Math.max(activitiesPage.totalPages, 1)}
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={() => setPageNumber((current) => Math.max(current - 1, 0))}
                                disabled={activitiesPage.first}
                                className="mo-btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                Previous
                            </button>
                            <button
                                onClick={() => setPageNumber((current) => current + 1)}
                                disabled={activitiesPage.last}
                                className="mo-btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                            >
                                Next
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {selectedSession ? (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
                    <div className="max-h-[90vh] w-full max-w-4xl overflow-hidden rounded-2xl border border-[#2A2A2A] bg-[#0F0F0F] shadow-2xl">
                        <div className="flex items-start justify-between gap-4 border-b border-[#202020] px-6 py-5">
                            <div>
                                <h2 className="text-xl font-semibold text-white">
                                    {selectedSession.summary || "Session Detail"}
                                </h2>
                                <div className="mt-2 text-sm text-[#A0A0A0]">
                                    {selectedSession.sessionId} - {formatDateTime(selectedSession.startedAt)}
                                </div>
                            </div>
                            <button
                                onClick={() => setSelectedSession(null)}
                                className="rounded-lg border border-[#2A2A2A] p-2 text-[#A0A0A0] hover:text-white"
                            >
                                <X className="h-4 w-4" />
                            </button>
                        </div>

                        <div className="grid max-h-[calc(90vh-96px)] gap-0 overflow-y-auto lg:grid-cols-[1.1fr_0.9fr]">
                            <div className="border-r border-[#202020] px-6 py-5">
                                <div className="mb-4">
                                    <div className="text-sm font-semibold text-white">Conversation</div>
                                    <div className="mt-1 text-xs text-[#A0A0A0]">
                                        {selectedSession.totalTurns || 0} turns - {selectedSession.duration || 0} seconds
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    {(selectedSession.messages || []).length === 0 ? (
                                        <div className="text-sm text-[#A0A0A0]">No transcript captured for this session.</div>
                                    ) : (
                                        (selectedSession.messages || []).map((message, index) => (
                                            <div
                                                key={`${message.timestamp || index}-${index}`}
                                                className={`rounded-2xl px-4 py-3 text-sm ${
                                                    message.role === "user"
                                                        ? "ml-8 bg-[#1A2512] text-white"
                                                        : "mr-8 bg-[#161616] text-[#E5E5E5]"
                                                }`}
                                            >
                                                <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-[#A0A0A0]">
                                                    {message.role === "user" ? "User" : "Assistant"}
                                                </div>
                                                <div>{message.content}</div>
                                                <div className="mt-2 text-[11px] text-[#7F7F7F]">
                                                    {formatDateTime(message.timestamp)}
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>

                            <div className="px-6 py-5">
                                <div className="mb-4">
                                    <div className="text-sm font-semibold text-white">Actions Taken</div>
                                    <div className="mt-1 text-xs text-[#A0A0A0]">
                                        {(selectedSession.activities || []).length} activity events
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    {(selectedSession.activities || []).length === 0 ? (
                                        <div className="text-sm text-[#A0A0A0]">No activity events were recorded.</div>
                                    ) : (
                                        (selectedSession.activities || []).map((activity, index) => {
                                            const ActivityIcon = getActivityIcon(activity.type);

                                            return (
                                                <div key={buildStableKey("session-activity", activity.id, activity.sessionId, activity.timestamp, index)} className="rounded-2xl border border-[#232323] bg-[#111111] p-4">
                                                    <div className="flex items-start gap-3">
                                                        <div className="rounded-xl border border-[#2A2A2A] bg-[#0D0D0D] p-2">
                                                            <ActivityIcon className="h-4 w-4 text-[#A0A0A0]" />
                                                        </div>
                                                        <div className="min-w-0 flex-1">
                                                            <div className="font-medium text-white">{activity.description}</div>
                                                            <div className="mt-2 flex flex-wrap items-center gap-2">
                                                                <span className="rounded-md border border-[#60A5FA40] bg-[#60A5FA20] px-2 py-1 text-[11px] font-semibold text-[#60A5FA]">
                                                                    {activity.agentName}
                                                                </span>
                                                                <span className={`rounded-md border px-2 py-1 text-[11px] font-semibold ${statusClassName(activity.status)}`}>
                                                                    {normalizeStatus(activity.status)}
                                                                </span>
                                                            </div>
                                                            <div className="mt-2 text-xs text-[#A0A0A0]">
                                                                {activity.type} - {formatDateTime(activity.timestamp)}
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    )}
                                </div>

                                {(selectedSession.tasksGenerated || []).length > 0 ? (
                                    <div className="mt-5 rounded-2xl border border-[#232323] bg-[#111111] p-4">
                                        <div className="text-sm font-semibold text-white">Tasks Generated</div>
                                        <ul className="mt-3 space-y-2 text-sm text-[#A0A0A0]">
                                            {(selectedSession.tasksGenerated || []).map((task, index) => (
                                                <li key={`${task}-${index}`}>{task}</li>
                                            ))}
                                        </ul>
                                    </div>
                                ) : null}
                            </div>
                        </div>
                    </div>
                </div>
            ) : null}

            {loadingSessionId ? (
                <div className="fixed bottom-6 right-6 rounded-xl border border-[#2A2A2A] bg-[#111111] px-4 py-3 text-sm text-white shadow-xl">
                    <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Loading session {loadingSessionId}
                    </div>
                </div>
            ) : null}
        </div>
    );
}
