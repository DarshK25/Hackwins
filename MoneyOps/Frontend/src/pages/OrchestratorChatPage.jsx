import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, useUser } from "@clerk/clerk-react";
import {
  ArrowLeft,
  Bot,
  ChevronDown,
  Clock3,
  X,
  Loader2,
  MessageSquare,
  PanelLeft,
  Plus,
  Send,
  Settings2,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { AiLoader } from "@/components/ui/ai-loader";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  deleteChatSession,
  listChatSessions,
  loadChatPreferences,
  saveChatPreferences,
  saveChatSession,
} from "@/lib/agentWorkspaceStorage";

function formatDateTime(value) {
  if (!value) return "No timestamp";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "No timestamp" : parsed.toLocaleString();
}

function buildSessionTitle(messages) {
  const firstUserMessage = messages.find((message) => message.role === "user")?.text;
  if (!firstUserMessage) return "New conversation";
  return firstUserMessage.length > 42 ? `${firstUserMessage.slice(0, 42)}...` : firstUserMessage;
}

function extractActions(payload) {
  const actions = [];
  if (payload?.ui_event?.type) {
    actions.push({
      type: payload.ui_event.type,
      title: payload.ui_event.title || payload.ui_event.type.replace(/_/g, " "),
      message: payload.ui_event.message || "",
      path: payload.ui_event.path || "",
      timestamp: new Date().toISOString(),
    });
  }
  if (payload?.tool_called) {
    actions.push({
      type: payload.tool_called,
      title: "Action completed",
      message: payload.intent || "",
      timestamp: new Date().toISOString(),
    });
  }
  return actions;
}

export default function OrchestratorChatPage() {
  const navigate = useNavigate();
  const { getToken } = useAuth();
  const { user } = useUser();
  const { userId: internalUserId, orgId: internalOrgId, loading: onboardingLoading } = useOnboardingStatus();

  const storageScope = `${internalOrgId || "org"}:${internalUserId || user?.id || "user"}`;
  const [hydrated, setHydrated] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(true);
  const [preferences, setPreferences] = useState({
    tone: "concise",
    rememberContext: true,
    autoOpenActions: true,
  });
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    const storedSessions = listChatSessions(storageScope);
    setSessions(storedSessions);
    setActiveSessionId(storedSessions[0]?.id || null);
    setPreferences(loadChatPreferences(storageScope));
  }, [hydrated, storageScope]);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) || null,
    [activeSessionId, sessions]
  );
  const activityFeed = activeSession?.actions || [];

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 220)}px`;
  }, [draft]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [activeSession?.messages?.length, sending]);

  function persistSessions(nextSessions, nextActiveId = activeSessionId) {
    setSessions(nextSessions);
    setActiveSessionId(nextActiveId);
  }

  function createSession(seedMessage = "") {
    const timestamp = new Date().toISOString();
    const session = {
      id: `chat-${Date.now()}`,
      title: seedMessage ? buildSessionTitle([{ role: "user", text: seedMessage }]) : "New conversation",
      createdAt: timestamp,
      updatedAt: timestamp,
      messages: [],
      actions: [],
    };
    saveChatSession(storageScope, session);
    const nextSessions = [session, ...sessions.filter((item) => item.id !== session.id)];
    persistSessions(nextSessions, session.id);
    return session;
  }

  function updateSession(sessionId, updater) {
    const sourceSessions = listChatSessions(storageScope);
    const sessionPool = sourceSessions.length ? sourceSessions : sessions;
    const current = sessionPool.find((session) => session.id === sessionId);
    if (!current) return null;
    const next = updater(current);
    saveChatSession(storageScope, next);
    const nextSessions = [next, ...sessionPool.filter((session) => session.id !== sessionId)];
    persistSessions(nextSessions, sessionId);
    return next;
  }

  function handleNewConversation() {
    createSession();
    setDraft("");
    toast.success("New conversation ready");
  }

  function handleDeleteConversation(sessionId) {
    const session = sessions.find((item) => item.id === sessionId);
    const label = session?.title || "this conversation";
    const confirmed = window.confirm(`Delete ${label}? This chat history will be removed from your saved workspace.`);
    if (!confirmed) {
      toast.message("Deletion cancelled");
      return;
    }
    const nextStored = deleteChatSession(storageScope, sessionId);
    const nextActive = activeSessionId === sessionId ? nextStored[0]?.id || null : activeSessionId;
    persistSessions(nextStored, nextActive);
    toast.success("Conversation deleted");
  }

  function handlePreferenceChange(key, value) {
    const nextPreferences = { ...preferences, [key]: value };
    setPreferences(nextPreferences);
    saveChatPreferences(storageScope, nextPreferences);
  }

  async function handleSend() {
    const text = draft.trim();
    if (!text || sending || onboardingLoading || !internalUserId || !internalOrgId) return;
    const startedAt = Date.now();

    const session = activeSession || createSession();
    const userMessage = {
      id: `msg-user-${Date.now()}`,
      role: "user",
      text,
      timestamp: new Date().toISOString(),
    };

    const preparedSession = updateSession(session.id, (current) => {
      const messages = [...(current.messages || []), userMessage];
      return {
        ...current,
        messages,
        updatedAt: userMessage.timestamp,
        title: buildSessionTitle(messages),
      };
    });

    setDraft("");
    setSending(true);

    try {
      const token = await getToken();
      const response = await fetch("/api/v1/voice/process", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          text,
          user_id: internalUserId,
          org_id: internalOrgId,
          session_id: session.id,
          context: {
            channel: "chat",
            agent_type: "orchestrator",
            preferences,
          },
          conversation_history: preferences.rememberContext ? preparedSession?.messages || [userMessage] : [userMessage],
        }),
      });

      const payload = await response.json();
      const actions = extractActions(payload);
      const agentMessage = {
        id: `msg-agent-${Date.now()}`,
        role: "agent",
        text: payload.response_text || "I've processed that.",
        timestamp: new Date().toISOString(),
        actions,
        reasoning_depth: Number(payload.reasoning_depth || (actions.length > 0 ? 1 : 0)),
        duration_ms: Number(payload.duration_ms || Date.now() - startedAt),
      };

      updateSession(session.id, (current) => {
        const messages = [...current.messages, agentMessage];
        return {
          ...current,
          messages,
          actions: [...(current.actions || []), ...actions].slice(-30),
          updatedAt: agentMessage.timestamp,
          title: buildSessionTitle(messages),
        };
      });

      if (payload.ui_event) {
        window.dispatchEvent(new CustomEvent("voice:agent-action", {
          detail: {
            type: payload.ui_event.type,
            title: payload.ui_event.title || payload.tool_called || "Agent action",
            message: payload.ui_event.message || payload.intent || "",
            timestamp: new Date().toISOString(),
            path: payload.ui_event.path || "",
          },
        }));
      }

      if (payload.ui_event && preferences.autoOpenActions) {
        window.dispatchEvent(new CustomEvent("voice:manual_ui_event", { detail: payload.ui_event }));
      }

      if (!payload.success) {
        toast.warning("The agent responded, but the action did not fully complete.");
      }
    } catch (error) {
      console.error("Failed to send chat message", error);
      toast.error("Failed to send message");
    } finally {
      setSending(false);
    }
  }

  if (!hydrated || onboardingLoading) {
    return (
      <div className="min-h-screen bg-[#0B0B0B]">
        <div className="flex min-h-screen items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen overflow-hidden bg-[#0B0B0B] text-white">
      <div className="flex h-screen">
        {sidebarOpen && (
          <aside className="flex h-screen w-full max-w-[320px] flex-col border-r border-[#2A2A2A] bg-[#111111]">
            <div className="flex items-center justify-between border-b border-[#2A2A2A] px-4 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[#A0A0A0]">Chat Workspace</p>
                <h1 className="mt-1 text-lg font-semibold text-white">Conversation History</h1>
              </div>
              <button onClick={handleNewConversation} className="rounded-lg border border-[#2A2A2A] p-2 text-[#A0A0A0] transition-colors hover:text-white">
                <Plus className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 space-y-2 overflow-y-auto p-3">
              {sessions.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#2A2A2A] p-4 text-sm text-[#A0A0A0]">
                  No chat sessions yet. Start the first one from the composer.
                </div>
              ) : (
                sessions.map((session) => (
                  <div
                    key={session.id}
                    className={`rounded-xl border p-3 transition-all ${
                      activeSessionId === session.id ? "border-[#4CBB1740] bg-[#4CBB1710]" : "border-[#2A2A2A] bg-[#151515]"
                    }`}
                  >
                    <button onClick={() => setActiveSessionId(session.id)} className="w-full text-left">
                      <div className="flex items-center gap-2">
                        <MessageSquare className="h-4 w-4 text-[#4CBB17]" />
                        <p className="truncate text-sm font-semibold text-white">{session.title}</p>
                      </div>
                      <p className="mt-2 text-xs text-[#A0A0A0]">{formatDateTime(session.updatedAt)}</p>
                      <p className="mt-1 text-xs text-[#A0A0A0]">{session.messages?.length || 0} messages</p>
                    </button>
                    <div className="mt-3 flex justify-end">
                      <button
                        onClick={() => handleDeleteConversation(session.id)}
                        className="rounded-md p-1.5 text-[#A0A0A0] transition-colors hover:bg-[#1F1F1F] hover:text-[#CD1C18]"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="border-t border-[#2A2A2A] p-3">
              <button
                onClick={() => setSettingsOpen(true)}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#151515] px-3 py-2 text-sm text-[#A0A0A0] transition-colors hover:text-white"
              >
                <Settings2 className="h-4 w-4" />
                Settings
              </button>
            </div>
          </aside>
        )}

        <main className="flex h-screen min-w-0 flex-1 flex-col">
          <div className="flex items-center justify-between border-b border-[#2A2A2A] px-5 py-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate("/orchestrator")}
                className="rounded-lg border border-[#2A2A2A] p-2 text-[#A0A0A0] transition-colors hover:text-white"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setSidebarOpen((current) => !current)}
                className="rounded-lg border border-[#2A2A2A] p-2 text-[#A0A0A0] transition-colors hover:text-white"
              >
                <PanelLeft className="h-4 w-4" />
              </button>
              <div>
                <h2 className="text-lg font-semibold text-white">Orchestrator Chat</h2>
                <p className="text-sm text-[#A0A0A0]">Chat with your MoneyOps assistant in a persistent, editable workspace.</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="max-w-[320px] truncate rounded-full border border-[#4CBB1740] bg-[#4CBB1710] px-3 py-1 text-xs text-[#4CBB17]">
                {activeSession ? activeSession.title : "No active conversation"}
              </div>
            </div>
          </div>

          <div className="flex min-h-0 flex-1">
            <section className="flex min-h-0 min-w-0 flex-1 flex-col">
              <div className="flex-1 overflow-y-auto px-5 py-5">
                <div className="mx-auto flex w-full max-w-4xl flex-col gap-1 pb-6">
                {!activeSession || activeSession.messages.length === 0 ? (
                  <div className="flex h-full min-h-[360px] flex-col items-center justify-center rounded-2xl border border-dashed border-[#2A2A2A] bg-[#111111] text-center">
                    <Bot className="mb-3 h-10 w-10 text-[#2A2A2A]" />
                    <p className="text-sm text-[#A0A0A0]">Start a conversation here for chat-based orchestrator actions.</p>
                  </div>
                ) : (
                  activeSession.messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex border-b border-[#161616] py-5 ${message.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[760px] px-1 ${
                          message.role === "user"
                            ? "text-white"
                            : "text-[#E6E6E6]"
                        }`}
                      >
                        <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#7A7A7A]">
                          {message.role === "user" ? "You" : "Orchestrator"}
                        </div>
                        <div
                          className={`${
                            message.role === "user"
                              ? "rounded-l-2xl rounded-r-md border border-[#4CBB1730] bg-[#4CBB170D] px-4 py-3 shadow-[0_10px_30px_rgba(76,187,23,0.08)]"
                              : "border-l border-[#4CBB1735] pl-4"
                          }`}
                        >
                          <p className="whitespace-pre-wrap text-sm leading-7">{message.text}</p>
                        </div>
                        {message.role === "agent" && message.reasoning_depth > 0 && message.duration_ms > 2000 && (
                          <button
                            type="button"
                            onClick={() => setActivityOpen(true)}
                            className="mt-3 flex items-center gap-2 pl-4 text-sm text-[#B9B9B9] transition-colors hover:text-white"
                          >
                            <Clock3 className="h-4 w-4 text-[#A0A0A0]" />
                            <span>
                              Thought for {(message.duration_ms / 1000).toFixed(1)}s
                              <span className="ml-1 text-[#8A8A8A]">›</span>
                            </span>
                          </button>
                        )}
                        <p className={`mt-3 text-[11px] ${message.role === "user" ? "text-[#7FAE6D]" : "text-[#707070]"}`}>
                          {formatDateTime(message.timestamp)}
                        </p>
                      </div>
                    </div>
                  ))
                )}
                {sending && (
                  <div className="flex justify-start border-b border-[#161616] py-5">
                    <div className="max-w-[760px] border-l border-[#4CBB1735] pl-4">
                      <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#7A7A7A]">
                        Orchestrator
                      </div>
                      <AiLoader text="Generating" size={118} className="justify-start py-3" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
                </div>
              </div>

              <div className="border-t border-[#161616] bg-[linear-gradient(180deg,rgba(11,11,11,0.2),#0B0B0B_22%)] px-5 pb-5 pt-3">
                <div className="mx-auto w-full max-w-4xl rounded-[28px] border border-[#2A2A2A] bg-[#111111] p-3 shadow-[0_-10px_40px_rgba(0,0,0,0.35)]">
                  <textarea
                    ref={textareaRef}
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder="Ask the orchestrator to create invoices, summarize collections, check compliance, run market updates, or act on workspace data..."
                    className="max-h-[220px] min-h-[72px] w-full resize-none overflow-y-auto bg-transparent px-1 py-1 text-sm text-white outline-none placeholder:text-[#666666]"
                  />
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <p className="text-xs text-[#A0A0A0]">Your conversation stays available for follow-up work.</p>
                    <button
                      onClick={handleSend}
                      disabled={!draft.trim() || sending}
                      className="mo-btn-primary flex items-center gap-2 disabled:opacity-50"
                    >
                      {sending ? (
                        <span className="relative flex h-4 w-4 items-center justify-center">
                          <span className="absolute inset-0 rounded-full border border-white/35 border-t-white animate-spin" />
                        </span>
                      ) : (
                        <Send className="h-4 w-4" />
                      )}
                      Send
                    </button>
                  </div>
                </div>
              </div>
            </section>

            {activityOpen && (
              <aside className="hidden h-full w-[340px] flex-col border-l border-[#2A2A2A] bg-[#101010] lg:flex">
                <div className="border-b border-[#1D1D1D] px-4 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#4CBB17]">Activity</p>
                      <h3 className="mt-1 text-lg font-semibold text-white">Agent trace</h3>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-[#7A7A7A]">
                        {activityFeed.length} event{activityFeed.length === 1 ? "" : "s"}
                      </span>
                      <button
                        type="button"
                        onClick={() => setActivityOpen(false)}
                        className="rounded-md p-1 text-[#8A8A8A] transition-colors hover:bg-[#171717] hover:text-white"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>

                <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
                  {activityFeed.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-[#2A2A2A] px-4 py-5 text-sm text-[#888888]">
                      Agent activity will appear here as soon as a response opens workspace flows.
                    </div>
                  ) : (
                    activityFeed
                      .slice()
                      .reverse()
                      .map((action, index) => (
                        <div key={`${action.type}-${action.timestamp}-${index}`} className="relative pl-5">
                          <span className="absolute left-0 top-1.5 h-2.5 w-2.5 rounded-full bg-[#4CBB17]" />
                          <div className="rounded-2xl border border-[#1D1D1D] bg-[#131313] px-4 py-3">
                            <p className="text-sm font-medium text-white">{action.title}</p>
                            {action.message ? <p className="mt-2 text-xs leading-5 text-[#9A9A9A]">{action.message}</p> : null}
                            {action.path ? <p className="mt-2 text-[11px] text-[#60A5FA]">{action.path}</p> : null}
                            <p className="mt-2 text-[11px] text-[#6F6F6F]">{formatDateTime(action.timestamp)}</p>
                          </div>
                        </div>
                      ))
                  )}
                </div>
              </aside>
            )}
          </div>
        </main>
      </div>

      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent className="border-[#2A2A2A] bg-[#111111] text-white sm:max-w-[460px]">
          <DialogHeader>
            <DialogTitle className="text-white">Chat Settings</DialogTitle>
            <DialogDescription className="text-[#A0A0A0]">
              Tune how the orchestrator responds and whether chat actions should open workspace flows automatically.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-[#A0A0A0]">Response style</label>
              <select
                value={preferences.tone}
                onChange={(event) => handlePreferenceChange("tone", event.target.value)}
                className="w-full rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none"
              >
                <option value="concise">Concise</option>
                <option value="balanced">Balanced</option>
                <option value="detailed">Detailed</option>
              </select>
            </div>

            <div className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">Remember context</p>
                  <p className="mt-1 text-xs text-[#A0A0A0]">Keep prior turns in the same session when you send the next message.</p>
                </div>
                <input
                  type="checkbox"
                  checked={preferences.rememberContext}
                  onChange={(event) => handlePreferenceChange("rememberContext", event.target.checked)}
                  className="h-4 w-4 accent-[#4CBB17]"
                />
              </div>
            </div>

            <div className="rounded-xl border border-[#2A2A2A] bg-[#151515] p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">Auto-run UI actions</p>
                  <p className="mt-1 text-xs text-[#A0A0A0]">Open invoice and client flows automatically when the response includes one.</p>
                </div>
                <input
                  type="checkbox"
                  checked={preferences.autoOpenActions}
                  onChange={(event) => handlePreferenceChange("autoOpenActions", event.target.checked)}
                  className="h-4 w-4 accent-[#4CBB17]"
                />
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
