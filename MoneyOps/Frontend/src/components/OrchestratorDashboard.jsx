import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  CheckCircle2,
  Clock,
  GitMerge,
  Loader2,
  Mic,
  RefreshCw,
  TrendingUp,
  Users,
  Wallet,
} from "lucide-react";
import { useAuth, useUser } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { listVoiceSessions } from "@/lib/agentWorkspaceStorage";

const STATUS_DOT = {
  completed: "#4CBB17",
  active: "#60A5FA",
  processing: "#60A5FA",
  in_progress: "#60A5FA",
  warning: "#FFB300",
  idle: "#3A3A3A",
  pending: "#3A3A3A",
};

const AGENT_STATUS_BADGE = {
  active: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
  processing: "bg-[#60A5FA20] text-[#60A5FA] border-[#60A5FA40]",
  warning: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
  idle: "bg-[#3A3A3A] text-[#A0A0A0] border-[#3A3A3A]",
};

function formatCurrency(value) {
  const amount = Number(value || 0);
  return `Rs ${amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function toDate(value) {
  if (!value) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  if (Array.isArray(value) && value.length >= 3) {
    const parsed = new Date(Number(value[0]), Number(value[1]) - 1, Number(value[2]));
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatDateTime(value) {
  const parsed = toDate(value);
  return parsed ? parsed.toLocaleString() : "No timestamp";
}

function normalizeCollection(payload) {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.data)) return payload.data;
  if (Array.isArray(payload?.items)) return payload.items;
  if (Array.isArray(payload?.activities)) return payload.activities;
  if (Array.isArray(payload?.conversations)) return payload.conversations;
  if (Array.isArray(payload?.transactions)) return payload.transactions;
  return [];
}

function StatCard({ label, value, sub, icon: Icon, iconColor }) {
  return (
    <div className="mo-card">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-medium uppercase tracking-wide text-[#A0A0A0]">{label}</p>
        {Icon && <Icon className="h-4 w-4" style={{ color: iconColor || "#A0A0A0" }} />}
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {sub && <p className="mt-1 text-xs text-[#A0A0A0]">{sub}</p>}
    </div>
  );
}

function buildDerivedActivities(serverActivities, invoices, transactions, clients) {
  const feed = [];

  normalizeCollection(serverActivities).forEach((activity, index) => {
    feed.push({
      id: activity.id || `server-${index}`,
      timestamp: activity.timestamp || activity.createdAt || activity.startedAt,
      description: activity.description || activity.summary || activity.type || "Orchestrator activity",
      status: activity.status || "completed",
      agent: activity.agent || "Orchestrator",
    });
  });

  invoices.forEach((invoice) => {
    const status = String(invoice.status || "DRAFT").toUpperCase();
    const invoiceNumber = invoice.invoiceNumber || invoice.id || "Draft invoice";
    const clientName = invoice.clientName || "Unknown client";
    const amount = formatCurrency(invoice.totalAmount || invoice.balanceDue || 0);
    const timestamp = invoice.updatedAt || invoice.issueDate || invoice.createdAt;

    feed.push({
      id: `invoice-${invoice.id || invoiceNumber}-${status}`,
      timestamp,
      status: status === "PAID" ? "completed" : status === "OVERDUE" ? "warning" : status === "DRAFT" ? "processing" : "active",
      agent: "Finance Agent",
      description:
        status === "PAID"
          ? `${invoiceNumber} was marked paid for ${clientName} (${amount})`
          : status === "OVERDUE"
            ? `${invoiceNumber} is overdue for ${clientName}`
            : status === "SENT"
              ? `${invoiceNumber} was sent to ${clientName}`
              : `${invoiceNumber} is in draft for ${clientName}`,
    });
  });

  transactions.forEach((transaction) => {
    const type = String(transaction.type || "").toUpperCase();
    const timestamp = transaction.transactionDate || transaction.date || transaction.createdAt;
    const amount = formatCurrency(transaction.amount || 0);
    const vendor = transaction.vendor || transaction.description || "Unlabeled transaction";

    feed.push({
      id: `txn-${transaction.id || vendor}-${timestamp || "na"}`,
      timestamp,
      status: "completed",
      agent: type === "INCOME" ? "Finance Agent" : "Orchestrator",
      description:
        type === "INCOME"
          ? `Recorded incoming payment of ${amount} from ${vendor}`
          : `Recorded expense of ${amount} for ${vendor}`,
    });
  });

  clients.forEach((client) => {
    const timestamp = client.updatedAt || client.createdAt;
    if (!timestamp) return;
    feed.push({
      id: `client-${client.id || client.name}-${timestamp}`,
      timestamp,
      status: "completed",
      agent: "Sales CRM",
      description: `Client profile updated for ${client.name || "Unnamed client"}`,
    });
  });

  return feed
    .filter((item) => item.timestamp)
    .sort((a, b) => (toDate(b.timestamp)?.getTime() || 0) - (toDate(a.timestamp)?.getTime() || 0))
    .slice(0, 16);
}

function inferMemoryAgent(memory) {
  const text = `${memory.type || ""} ${memory.content || ""} ${(memory.tags || []).join(" ")}`.toLowerCase();
  if (["market", "competitor", "opportunity", "growth", "research", "news"].some((token) => text.includes(token))) return "Market Agent";
  if (["tax", "gst", "tds", "compliance", "filing", "audit"].some((token) => text.includes(token))) return "Compliance Agent";
  if (["invoice", "revenue", "cash", "payment", "expense", "transaction"].some((token) => text.includes(token))) return "Finance Agent";
  if (["client", "lead", "customer", "pipeline", "sales"].some((token) => text.includes(token))) return "Sales CRM";
  return "Orchestrator";
}

function isSensitiveMemory(memory) {
  const content = String(memory?.content || "");
  const tags = Array.isArray(memory?.tags) ? memory.tags.join(" ").toLowerCase() : "";
  const combined = `${String(memory?.type || "")} ${content} ${tags}`.toLowerCase();

  return [
    "security code",
    "team security code",
    "team action code",
    "otp",
    "pin",
    "passcode",
    "password",
    "secret",
    "token",
    "auth token",
  ].some((token) => combined.includes(token)) || /\b(code|pin|otp|passcode)\s*(is|:)?\s*\d{4,8}\b/i.test(content);
}

function buildMemoryTrail(memories) {
  return memories
    .filter((memory) => !isSensitiveMemory(memory))
    .map((memory, index) => ({
      id: memory.id || `memory-${index}`,
      agent: inferMemoryAgent(memory),
      type: memory.type || "memory",
      content: memory.content || "No memory content",
      source: memory.source || "system",
      timestamp: memory.lastReferencedAt || memory.createdAt,
      tags: memory.tags || [],
    }))
    .sort((a, b) => (toDate(b.timestamp)?.getTime() || 0) - (toDate(a.timestamp)?.getTime() || 0))
    .slice(0, 18);
}

export function OrchestratorDashboard({ businessId = 1 }) {
  const { getToken } = useAuth();
  const { user } = useUser();
  const { userId: internalUserId, orgId: internalOrgId } = useOnboardingStatus();
  const resolvedBusinessId = businessId || 1;
  const storageScope = `${internalOrgId || "org"}:${internalUserId || user?.id || "user"}`;

  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("operations");
  const [orgProfile, setOrgProfile] = useState(null);
  const [clients, setClients] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [activities, setActivities] = useState([]);
  const [backendConversations, setBackendConversations] = useState([]);
  const [memories, setMemories] = useState([]);
  const [localVoiceSessions, setLocalVoiceSessions] = useState([]);

  useEffect(() => {
    if (internalOrgId && user?.id) {
      fetchOrchestratorData();
    }
  }, [internalOrgId, user?.id]);

  async function fetchJson(url, headers) {
    const response = await fetch(url, { headers });
    if (!response.ok) throw new Error(`Failed to fetch ${url}`);
    return response.json();
  }

  async function fetchOptionalJson(url, headers, emptyValue) {
    try {
      const response = await fetch(url, { headers });
      if (!response.ok) return emptyValue;
      return await response.json();
    } catch {
      return emptyValue;
    }
  }

  async function fetchOrchestratorData() {
    try {
      setLoading(true);
      const token = await getToken();
      const headers = {
        Authorization: `Bearer ${token}`,
        "X-User-Id": internalUserId || user?.id,
        "X-Org-Id": internalOrgId,
      };

      const [
        orgRes,
        clientsRes,
        invoicesRes,
        transactionsRes,
        metricsRes,
        activitiesRes,
        conversationsRes,
        memoryRes,
      ] = await Promise.all([
        fetchJson("/api/org/my", headers),
        fetchJson("/api/clients", headers),
        fetchJson("/api/invoices", headers),
        fetchJson("/api/transactions", headers),
        fetchOptionalJson(`/api/finance-intelligence/metrics?businessId=${resolvedBusinessId}`, headers, null),
        fetchOptionalJson(`/api/orchestrator/activities?businessId=${resolvedBusinessId}`, headers, { activities: [] }),
        fetchOptionalJson(`/api/orchestrator/conversations?businessId=${resolvedBusinessId}`, headers, { conversations: [] }),
        fetchOptionalJson(`/api/memory/${internalOrgId}?limit=60`, headers, []),
      ]);

      setOrgProfile(orgRes?.data || orgRes || null);
      setClients(normalizeCollection(clientsRes));
      setInvoices(normalizeCollection(invoicesRes));
      setTransactions(normalizeCollection(transactionsRes));
      setMetrics(metricsRes);
      setActivities(normalizeCollection(activitiesRes));
      setBackendConversations(normalizeCollection(conversationsRes));
      setMemories(normalizeCollection(memoryRes));
      setLocalVoiceSessions(listVoiceSessions(storageScope));
    } catch (error) {
      console.error("Failed to load orchestrator data", error);
      setOrgProfile(null);
      setClients([]);
      setInvoices([]);
      setTransactions([]);
      setMetrics(null);
      setActivities([]);
      setBackendConversations([]);
      setMemories([]);
      setLocalVoiceSessions(listVoiceSessions(storageScope));
    } finally {
      setLoading(false);
    }
  }

  const now = new Date();
  const currentMonth = now.getMonth();
  const currentYear = now.getFullYear();

  const invoiceSummary = useMemo(() => {
    const summary = { draft: 0, sent: 0, paid: 0, overdue: 0, totalValue: 0, outstandingValue: 0 };
    invoices.forEach((invoice) => {
      const status = String(invoice.status || "DRAFT").toUpperCase();
      const totalAmount = Number(invoice.totalAmount || 0);
      const balanceDue = Number(invoice.balanceDue ?? totalAmount);
      if (status === "PAID") summary.paid += 1;
      else if (status === "SENT") summary.sent += 1;
      else if (status === "OVERDUE") summary.overdue += 1;
      else summary.draft += 1;
      summary.totalValue += totalAmount;
      if (status !== "PAID") summary.outstandingValue += balanceDue;
    });
    return summary;
  }, [invoices]);

  const transactionSummary = useMemo(() => {
    let inflow = 0;
    let outflow = 0;
    let monthInflow = 0;
    let monthOutflow = 0;
    transactions.forEach((transaction) => {
      const amount = Math.abs(Number(transaction.amount || 0));
      const type = String(transaction.type || "").toUpperCase();
      const txnDate = toDate(transaction.transactionDate || transaction.date || transaction.createdAt);
      if (type === "INCOME") {
        inflow += amount;
        if (txnDate && txnDate.getMonth() === currentMonth && txnDate.getFullYear() === currentYear) monthInflow += amount;
      } else {
        outflow += amount;
        if (txnDate && txnDate.getMonth() === currentMonth && txnDate.getFullYear() === currentYear) monthOutflow += amount;
      }
    });
    return { inflow, outflow, monthInflow, monthOutflow, netCash: inflow - outflow };
  }, [transactions, currentMonth, currentYear]);

  const clientSummary = useMemo(() => {
    const thisMonth = clients.filter((client) => {
      const createdAt = toDate(client.createdAt || client.updatedAt);
      return createdAt && createdAt.getMonth() === currentMonth && createdAt.getFullYear() === currentYear;
    });
    return { total: clients.length, newThisMonth: thisMonth.length };
  }, [clients, currentMonth, currentYear]);

  const recentActivities = useMemo(
    () => buildDerivedActivities(activities, invoices, transactions, clients),
    [activities, invoices, transactions, clients]
  );

  const marketMemories = useMemo(
    () => memories.filter((memory) => inferMemoryAgent(memory) === "Market Agent"),
    [memories]
  );

  const priorities = useMemo(() => {
    const items = [];
    if (invoiceSummary.overdue > 0) items.push(`${invoiceSummary.overdue} overdue invoices need follow-up.`);
    if (invoiceSummary.draft > 0) items.push(`${invoiceSummary.draft} draft invoices are waiting for review or sending.`);
    if (transactionSummary.monthOutflow > transactionSummary.monthInflow) items.push("This month's cash outflow is running ahead of inflow.");
    if (!marketMemories.length) items.push("No recent market-intelligence memory was found. Run a market update if you want that agent to become active.");
    if (!items.length) items.push("All core operational queues look stable right now.");
    return items.slice(0, 4);
  }, [invoiceSummary, transactionSummary, marketMemories]);

  const agentStatuses = useMemo(() => {
    const revenue = Number(metrics?.revenue || invoiceSummary.totalValue || 0);
    return [
      {
        name: "Finance Agent",
        status: invoiceSummary.overdue > 0 ? "warning" : invoices.length || transactions.length ? "active" : "idle",
        tasksCompleted: invoices.length + transactions.length,
        lastActivity: recentActivities.find((item) => item.agent === "Finance Agent")?.timestamp,
        currentTask:
          invoiceSummary.overdue > 0
            ? `${invoiceSummary.overdue} overdue invoices need follow-up`
            : invoices.length
              ? `Monitoring ${invoices.length} invoices and ${transactions.length} transactions`
              : "Waiting for invoice or transaction activity",
      },
      {
        name: "Sales CRM",
        status: clientSummary.total > 0 ? "active" : "idle",
        tasksCompleted: clientSummary.total,
        lastActivity: recentActivities.find((item) => item.agent === "Sales CRM")?.timestamp,
        currentTask:
          clientSummary.total > 0
            ? `Tracking ${clientSummary.total} clients with ${clientSummary.newThisMonth} added this month`
            : "Waiting for client records",
      },
      {
        name: "Compliance Agent",
        status: invoiceSummary.overdue > 0 || invoiceSummary.draft > 0 ? "processing" : invoices.length ? "active" : "idle",
        tasksCompleted: invoices.length,
        lastActivity: recentActivities.find((item) => item.agent === "Compliance Agent")?.timestamp,
        currentTask:
          invoiceSummary.overdue > 0
            ? `Reviewing ${invoiceSummary.overdue} overdue payment obligations`
            : invoices.length
              ? `Watching GST and due-date coverage across ${invoices.length} invoices`
              : "No invoice compliance workload yet",
      },
      {
        name: "Market Agent",
        status: marketMemories.length > 0 ? "active" : "idle",
        tasksCompleted: marketMemories.length,
        lastActivity: marketMemories[0]?.lastReferencedAt || marketMemories[0]?.createdAt,
        currentTask:
          marketMemories.length > 0
            ? `Using ${marketMemories.length} recent market-intelligence memories with ${clientSummary.total} clients and ${formatCurrency(revenue)} billed value`
            : "No recent market update queries were saved yet",
      },
      {
        name: "Orchestrator",
        status: recentActivities.length || localVoiceSessions.length ? "active" : "idle",
        tasksCompleted: recentActivities.length + localVoiceSessions.length,
        lastActivity: recentActivities[0]?.timestamp || localVoiceSessions[0]?.endedAt,
        currentTask: priorities[0],
      },
    ];
  }, [clientSummary, invoiceSummary, invoices.length, localVoiceSessions, marketMemories, metrics?.revenue, priorities, recentActivities, transactions.length]);

  const activeAgentCount = agentStatuses.filter((agent) => agent.status !== "idle").length;
  const orgName = orgProfile?.legalName || orgProfile?.tradingName || "MoneyOps Workspace";
  const memoryTrail = useMemo(() => buildMemoryTrail(memories), [memories]);
  const voiceHistory = useMemo(() => {
    if (backendConversations.length) return backendConversations;
    return localVoiceSessions;
  }, [backendConversations, localVoiceSessions]);

  const tabs = [
    { id: "operations", label: "Operations Feed" },
    { id: "conversations", label: "Voice History" },
    { id: "agents", label: "Agent Network" },
  ];

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4">
          <div className="rounded-xl border p-3" style={{ backgroundColor: "#60A5FA20", borderColor: "#60A5FA40" }}>
            <GitMerge className="h-6 w-6 text-[#60A5FA]" />
          </div>
          <div>
            <h1 className="mo-h1">Orchestrator Command Center</h1>
            <p className="mo-text-secondary mt-0.5">Real-time workspace overview for {orgName}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchOrchestratorData} className="mo-btn-secondary flex items-center gap-2 text-sm">
            <RefreshCw className="h-4 w-4" /> Refresh
          </button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Active Agents" value={`${activeAgentCount} / ${agentStatuses.length}`} sub="Based on current signals and saved activity" icon={Users} iconColor="#60A5FA" />
        <StatCard label="Open Receivables" value={formatCurrency(invoiceSummary.outstandingValue)} sub={`${invoiceSummary.overdue} overdue invoices`} icon={AlertTriangle} iconColor="#FFB300" />
        <StatCard label="Cash Position" value={formatCurrency(transactionSummary.netCash)} sub={`This month: in ${formatCurrency(transactionSummary.monthInflow)} / out ${formatCurrency(transactionSummary.monthOutflow)}`} icon={Wallet} iconColor="#4CBB17" />
        <StatCard label="Voice Workflows" value={String(voiceHistory.length)} sub="Saved voice sessions and action history" icon={Mic} iconColor="#4CBB17" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.4fr,0.9fr]">
        <div className="mo-card">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="mo-h2 mb-1">Operational Priorities</h2>
              <p className="text-sm text-[#A0A0A0]">What the orchestrator should push you toward next</p>
            </div>
            <TrendingUp className="h-5 w-5 text-[#4CBB17]" />
          </div>
          <div className="flex flex-col gap-3">
            {priorities.map((priority, index) => (
              <div key={index} className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-[#A0A0A0]">Priority {index + 1}</p>
                <p className="mt-1 text-sm text-white">{priority}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="mo-card">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="mo-h2 mb-1">Workspace Pulse</h2>
              <p className="text-sm text-[#A0A0A0]">The business facts currently driving the orchestration layer</p>
            </div>
            <Activity className="h-5 w-5 text-[#60A5FA]" />
          </div>
          <div className="grid gap-3">
            <div className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
              <p className="text-xs uppercase tracking-wide text-[#A0A0A0]">Invoice Pipeline</p>
              <p className="mt-2 text-lg font-semibold text-white">{invoiceSummary.draft} draft, {invoiceSummary.sent} sent, {invoiceSummary.paid} paid</p>
              <p className="mt-1 text-xs text-[#A0A0A0]">Total billed value {formatCurrency(invoiceSummary.totalValue)}</p>
            </div>
            <div className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
              <p className="text-xs uppercase tracking-wide text-[#A0A0A0]">Client Base</p>
              <p className="mt-2 text-lg font-semibold text-white">{clientSummary.total} active client records</p>
              <p className="mt-1 text-xs text-[#A0A0A0]">{clientSummary.newThisMonth} updated or added this month</p>
            </div>
            <div className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
              <p className="text-xs uppercase tracking-wide text-[#A0A0A0]">Collections</p>
              <p className="mt-2 text-lg font-semibold text-white">{formatCurrency(metrics?.revenue || 0)}</p>
              <p className="mt-1 text-xs text-[#A0A0A0]">Collection rate {Number(metrics?.collectionRate || 0).toFixed(0)}%</p>
            </div>
            <div className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
              <p className="text-xs uppercase tracking-wide text-[#A0A0A0]">Cash Movements</p>
              <p className="mt-2 text-lg font-semibold text-white">{transactions.length} recorded entries</p>
              <p className="mt-1 text-xs text-[#A0A0A0]">Inflow {formatCurrency(transactionSummary.inflow)} / Outflow {formatCurrency(transactionSummary.outflow)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="mo-card !p-0">
        <div className="flex border-b border-[#2A2A2A] px-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`border-b-2 px-4 py-3.5 text-sm font-medium transition-colors ${
                activeTab === tab.id ? "border-[#4CBB17] text-[#4CBB17]" : "border-transparent text-[#A0A0A0] hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-5">
          {activeTab === "operations" && (
            <div className="flex flex-col gap-3">
              {!recentActivities.length ? (
                <div className="flex flex-col items-center py-16 text-center">
                  <Activity className="mb-3 h-10 w-10 text-[#2A2A2A]" />
                  <p className="text-sm text-[#A0A0A0]">No recent business activity yet.</p>
                </div>
              ) : (
                recentActivities.map((activity) => (
                  <div key={activity.id} className="flex gap-3 rounded-xl border border-[#2A2A2A] p-3 transition-all hover:border-[#3A3A3A]">
                    <div className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full" style={{ backgroundColor: STATUS_DOT[activity.status] || "#3A3A3A" }} />
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-white">{activity.description}</span>
                        {activity.agent && <span className="rounded-md border border-[#60A5FA40] bg-[#60A5FA20] px-2 py-0.5 text-xs text-[#60A5FA]">{activity.agent}</span>}
                      </div>
                      <p className="mt-1 flex items-center gap-1 text-xs text-[#A0A0A0]">
                        <Clock className="h-3 w-3" /> {formatDateTime(activity.timestamp)}
                      </p>
                    </div>
                    {activity.status === "completed" && <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-[#4CBB17]" />}
                    {(activity.status === "processing" || activity.status === "in_progress") && <Loader2 className="h-5 w-5 animate-spin text-[#60A5FA]" />}
                    {activity.status === "warning" && <AlertTriangle className="h-5 w-5 flex-shrink-0 text-[#FFB300]" />}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === "conversations" && (
            <div className="flex flex-col gap-4">
              {!voiceHistory.length ? (
                <div className="flex flex-col items-center py-16 text-center">
                  <MessageSquare className="mb-3 h-10 w-10 text-[#2A2A2A]" />
                  <p className="text-sm text-[#A0A0A0]">No saved voice sessions yet.</p>
                  <p className="mt-1 text-xs text-[#A0A0A0]">New voice calls will appear here with transcript snippets and action history.</p>
                </div>
              ) : (
                voiceHistory.map((conversation, index) => {
                  const transcript = normalizeCollection(conversation.transcript || conversation.messages);
                  const actions = normalizeCollection(conversation.actions);
                  const startedAt = conversation.startedAt || conversation.createdAt || conversation.timestamp;
                  return (
                    <div key={conversation.id || `voice-${index}`} className="overflow-hidden rounded-xl border border-[#2A2A2A]">
                      <div className="flex items-center justify-between border-b border-[#2A2A2A] p-4">
                        <div className="flex items-center gap-2">
                          <Mic className="h-4 w-4 text-[#4CBB17]" />
                          <span className="text-sm font-semibold text-white">{conversation.summary || "Voice conversation"}</span>
                        </div>
                        <span className="rounded-full border border-[#A0A0A040] bg-[#A0A0A020] px-2 py-0.5 text-xs text-[#A0A0A0]">
                          saved
                        </span>
                      </div>
                      <div className="flex flex-col gap-3 p-4">
                        <p className="text-xs text-[#A0A0A0]">{formatDateTime(startedAt)}</p>
                        {actions.length > 0 && (
                          <div className="rounded-lg bg-[#151515] p-3">
                            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-[#A0A0A0]">Actions triggered</p>
                            <div className="flex flex-col gap-2">
                              {actions.map((action, actionIndex) => (
                                <div key={actionIndex} className="flex items-start gap-2 text-sm text-white">
                                  <ArrowRight className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-[#4CBB17]" />
                                  <div>
                                    <p>{action.title || action.type}</p>
                                    {action.message && <p className="text-xs text-[#A0A0A0]">{action.message}</p>}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        <div className="flex flex-col gap-2">
                          {transcript.slice(0, 4).map((message, messageIndex) => (
                            <div
                              key={message.id || messageIndex}
                              className={`rounded-lg p-2.5 text-sm ${
                                message.role === "user" ? "ml-8 bg-[#4CBB1715] text-white" : "mr-8 bg-[#1A1A1A] text-[#A0A0A0]"
                              }`}
                            >
                              <p className="mb-1 text-xs font-semibold text-[#A0A0A0]">{message.role === "user" ? "You" : "Agent"}</p>
                              <p>{message.text || message.content}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {activeTab === "agents" && (
            <div className="flex flex-col gap-6">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {agentStatuses.map((agent) => (
                  <div key={agent.name} className="rounded-xl border border-[#2A2A2A] p-4 transition-all hover:border-[#3A3A3A]">
                    <div className="mb-3 flex items-center justify-between">
                      <h4 className="font-semibold text-white">{agent.name}</h4>
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-2 rounded-full" style={{ backgroundColor: STATUS_DOT[agent.status] || "#3A3A3A" }} />
                        <span className={`rounded-full border px-2 py-0.5 text-xs ${AGENT_STATUS_BADGE[agent.status] || AGENT_STATUS_BADGE.idle}`}>{agent.status}</span>
                      </div>
                    </div>
                    <div className="flex flex-col gap-1.5 text-sm">
                      <div className="flex justify-between">
                        <span className="text-[#A0A0A0]">Signals Processed</span>
                        <span className="font-semibold text-white">{agent.tasksCompleted}</span>
                      </div>
                      <div className="flex justify-between gap-3">
                        <span className="text-[#A0A0A0]">Last Activity</span>
                        <span className="text-right font-semibold text-white">{agent.lastActivity ? formatDateTime(agent.lastActivity) : "No recent activity"}</span>
                      </div>
                      <div className="mt-2 rounded-lg bg-[#1A1A1A] p-2.5 text-sm text-[#A0A0A0]">{agent.currentTask}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] p-5">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-semibold text-white">Agent Memory Trail</h3>
                    <p className="text-sm text-[#A0A0A0]">Recent memory and recall history across the agent network</p>
                  </div>
                  <Bot className="h-5 w-5 text-[#60A5FA]" />
                </div>
                {!memoryTrail.length ? (
                  <div className="rounded-xl border border-dashed border-[#2A2A2A] p-8 text-center">
                    <p className="text-sm text-[#A0A0A0]">No saved agent memories were returned yet.</p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-3">
                    {memoryTrail.map((memory) => (
                      <div key={memory.id} className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-md border border-[#60A5FA40] bg-[#60A5FA20] px-2 py-0.5 text-xs text-[#60A5FA]">{memory.agent}</span>
                          <span className="rounded-md border border-[#A0A0A040] bg-[#A0A0A020] px-2 py-0.5 text-xs text-[#A0A0A0]">{memory.type}</span>
                          <span className="text-xs text-[#A0A0A0]">{formatDateTime(memory.timestamp)}</span>
                        </div>
                        <p className="mt-2 text-sm text-white">{memory.content}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {memory.tags.slice(0, 4).map((tag) => (
                            <span key={tag} className="rounded-md bg-[#1F1F1F] px-2 py-0.5 text-[11px] text-[#A0A0A0]">
                              #{tag}
                            </span>
                          ))}
                          <span className="rounded-md bg-[#1F1F1F] px-2 py-0.5 text-[11px] text-[#A0A0A0]">source: {memory.source}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
