import { useState, useCallback, useEffect, useRef } from "react";
import { useUser } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { X, Phone, PhoneOff } from "lucide-react";
import { toast } from "sonner";
import {
    LiveKitRoom,
    RoomAudioRenderer,
    useConnectionState,
    useRoomContext,
    ConnectionState,
} from "@livekit/components-react";
import "@livekit/components-styles";
import { AIVoiceInput } from "@/components/ui/ai-voice-input";
import { motion, AnimatePresence } from "framer-motion";
import { useVoiceEvents } from "@/hooks/useVoiceEvents";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import ClientInputDialog from "./ClientInputDialog";

const PROVIDER_STATUS_LABELS = {
    missing_api_key: "API key is empty",
    invalid_api_key: "API key is invalid",
    limit_reached: "API limit is reached",
    provider_unreachable: "Provider could not be reached",
    provider_error: "Provider check failed",
};

function buildProviderIssue(provider, envVar, status, severity, message) {
    return {
        provider,
        env_var: envVar,
        status,
        severity,
        message,
    };
}

function inferProviderStatusFromText(text) {
    const normalizedText = (text || "").toLowerCase();
    const issues = [];

    if (normalizedText.includes("groq")) {
        if (normalizedText.includes("api key") && /(empty|missing|required)/.test(normalizedText)) {
            issues.push(
                buildProviderIssue(
                    "Groq",
                    "GROQ_API_KEY",
                    "missing_api_key",
                    "blocking",
                    "Groq API key is empty. Add GROQ_API_KEY before starting the voice agent."
                )
            );
        } else if (/(limit|quota|credit|429|rate)/.test(normalizedText)) {
            issues.push(
                buildProviderIssue(
                    "Groq",
                    "GROQ_API_KEY",
                    "limit_reached",
                    "blocking",
                    "Groq API limit is reached or quota is over."
                )
            );
        }
    }

    if (normalizedText.includes("cartesia")) {
        if (normalizedText.includes("api key") && /(empty|missing|required)/.test(normalizedText)) {
            issues.push(
                buildProviderIssue(
                    "Cartesia",
                    "CARTESIA_API_KEY",
                    "missing_api_key",
                    "warning",
                    "Cartesia API key is empty. Voice will fall back to Groq TTS."
                )
            );
        } else if (/(limit|quota|credit|429|rate)/.test(normalizedText)) {
            issues.push(
                buildProviderIssue(
                    "Cartesia",
                    "CARTESIA_API_KEY",
                    "limit_reached",
                    "warning",
                    "Cartesia API limit is reached or quota is over. Voice will fall back to Groq TTS."
                )
            );
        }
    }

    if (!issues.length) {
        return null;
    }

    return {
        blocking: issues.some((issue) => issue.severity === "blocking"),
        issues,
    };
}

function normalizeProviderStatus(rawStatus, fallbackText = "") {
    const providerStatus = rawStatus?.provider_status ?? rawStatus;
    const issues = Array.isArray(providerStatus?.issues)
        ? providerStatus.issues
        : inferProviderStatusFromText(fallbackText)?.issues;

    if (!issues?.length) {
        return null;
    }

    return {
        blocking:
            typeof providerStatus?.blocking === "boolean"
                ? providerStatus.blocking
                : issues.some((issue) => issue?.severity === "blocking"),
        issues,
        message: providerStatus?.message || "",
    };
}

function buildStableKey(prefix, ...parts) {
    const normalizedParts = parts
        .map((part) => (part == null ? "" : String(part).trim()))
        .filter(Boolean);

    return [prefix, ...normalizedParts].join("-");
}

async function parseVoiceTokenFailure(res) {
    const contentType = res.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
        const json = await res.json().catch(() => null);
        const detail = json?.detail ?? json;
        const detailMessage = typeof detail === "string"
            ? detail
            : detail?.message || detail?.detail || "";
        const providerStatus = normalizeProviderStatus(
            detail?.provider_status ? detail : json,
            detailMessage
        );

        return {
            message: detailMessage,
            providerStatus,
        };
    }

    const text = await res.text();
    return {
        message: text,
        providerStatus: normalizeProviderStatus(null, text),
    };
}

export function VoiceCallAgent({ agentType = "orchestrator" }) {
    const { user, isLoaded } = useUser();
    const { userId: internalUserId, orgId: internalOrgId, loading: onboardingLoading } = useOnboardingStatus();
    const [isVisible, setIsVisible] = useState(true);
    const [token, setToken] = useState("");
    const [url, setUrl] = useState("");
    const [isConnect, setIsConnect] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isInputLocked, setIsInputLocked] = useState(false);  // ── INPUT RATE LIMITING
    const [activeDialog, setActiveDialog] = useState(null);
    const [activeClientPicker, setActiveClientPicker] = useState(null);
    const [providerPopup, setProviderPopup] = useState({
        open: false,
        blocking: false,
        issues: [],
        message: "",
    });

    const showProviderPopup = useCallback((providerStatus, fallbackMessage = "") => {
        const normalizedStatus = normalizeProviderStatus(providerStatus, fallbackMessage);
        if (!normalizedStatus) {
            return false;
        }

        setProviderPopup({
            open: true,
            blocking: normalizedStatus.blocking,
            issues: normalizedStatus.issues,
            message: normalizedStatus.message || fallbackMessage,
        });
        return true;
    }, []);

    const handleClientPick = async (client) => {
        if (!activeClientPicker?.session_id) return;
        
        // ── PREVENT SIMULTANEOUS INPUT ────────────────────────────────────────────
        if (isInputLocked) {
            toast.error("Please wait for the current input to be processed.");
            return;
        }
        
        setIsInputLocked(true);  // Lock input while processing
        try {
            const res = await fetch("/api/v1/voice/dialog-response", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: activeClientPicker.session_id,
                    dialog_id: "invoice_preview_form",
                    fields: { client_name: client.name, client_id: client.id },
                }),
            });
            const data = await res.json();
            
            // ── CHECK FOR PROCESSING LOCK ERROR ───────────────────────────────────
            if (data?.is_locked) {
                toast.error("Voice input is currently being processed. Please wait.");
                return;
            }
            
            if (data?.message) {
                window.dispatchEvent(new CustomEvent("voice:manual_agent_response", {
                    detail: {
                        responseText: data.message,
                        uiEvent: data.ui_event || null,
                    },
                }));
            }
            if (data?.ui_event) {
                window.dispatchEvent(new CustomEvent("voice:open_client_picker", { detail: null }));
                window.dispatchEvent(new CustomEvent("voice:manual_ui_event", { detail: data.ui_event }));
            }
            setActiveClientPicker(null);
        } catch (error) {
            console.error("Failed to select client", error);
            toast.error("Failed to select client");
        } finally {
            setIsInputLocked(false);  // Unlock input
        }
    };

    const startCall = async () => {
        if (!user?.id) {
            toast.error("Please sign in to start a voice call.");
            return;
        }
        if (onboardingLoading || !internalUserId || !internalOrgId) {
            toast.error("Voice agent is waiting for your workspace context. Please try again in a moment.");
            return;
        }
        setActiveDialog(null);
        setActiveClientPicker(null);
        setIsProcessing(true);
        try {
            const userId = internalUserId;
            const sessionToken = await window.Clerk?.session?.getToken();
            const orgId = internalOrgId;
            const metadata = JSON.stringify({
                user_id: userId,
                org_id: orgId,
                user_name: user.fullName || user.username || "User",
                auth_token: sessionToken || "",
            });
            const params = new URLSearchParams({ user_id: userId, org_id: orgId, metadata });
            const res = await fetch(`/api/v1/voice/token?${params.toString()}`, {
                headers: {
                    "Authorization": `Bearer ${sessionToken}`,
                    "X-User-Id": userId,
                    "X-Org-Id": orgId
                }
            });
            if (!res.ok) {
                const { message, providerStatus } = await parseVoiceTokenFailure(res);
                if (providerStatus) {
                    showProviderPopup(providerStatus, message);
                    setIsProcessing(false);
                    setIsConnect(false);
                    return;
                }
                throw new Error(message || `Failed to fetch token (${res.status})`);
            }
            const contentType = res.headers.get("content-type");
            if (!contentType?.includes("application/json")) {
                throw new Error(
                    "Server returned non-JSON. Is AI Gateway running on port 8001? " +
                    "Restart the dev server after adding the proxy."
                );
            }
            const data = await res.json();
            if (!data.token || !data.url) throw new Error("Invalid token response: missing token or url");
            showProviderPopup(data.provider_status);
            setToken(data.token);
            setUrl(data.url);
            setIsConnect(true);
            setIsProcessing(false);
        } catch (error) {
            console.error("Failed to start call:", error);
            const message = error?.message?.includes("non-JSON")
                ? "AI Gateway not reachable. Check it's running on port 8001 and has LIVEKIT_* in .env"
                : "Failed to start voice agent";
            toast.error(message);
            setIsProcessing(false);
            setIsConnect(false);
        }
    };

    const disconnect = useCallback(() => {
        setIsConnect(false);
        setToken("");
        setIsProcessing(false);
        setIsInputLocked(false);  // ── RESET INPUT LOCK ON DISCONNECT
        setActiveDialog(null);
        setActiveClientPicker(null);
    }, []);

    useEffect(() => {
        const clearInteractiveState = () => {
            setActiveDialog(null);
            setActiveClientPicker(null);
        };
        const handleOpenDialog = (e) => {
            setActiveClientPicker(null);
            setActiveDialog(e.detail || null);
        };
        const handleOpenClientPicker = (e) => {
            setActiveDialog(null);
            setActiveClientPicker(e.detail || null);
        };
        const handleConversationUpdate = (e) => {
            const uiEventType = e?.detail?.ui_event?.type;
            if (uiEventType !== "open_input_dialog") {
                setActiveDialog(null);
            }
            if (uiEventType !== "open_client_picker") {
                setActiveClientPicker(null);
            }
        };
        window.addEventListener("voice:open_input_dialog", handleOpenDialog);
        window.addEventListener("voice:open_client_picker", handleOpenClientPicker);
        window.addEventListener("voice:conversation_update", handleConversationUpdate);
        window.addEventListener("voice:client-created", clearInteractiveState);
        window.addEventListener("voice:invoice-created", clearInteractiveState);
        window.addEventListener("voice:expense-created", clearInteractiveState);
        return () => {
            window.removeEventListener("voice:open_input_dialog", handleOpenDialog);
            window.removeEventListener("voice:open_client_picker", handleOpenClientPicker);
            window.removeEventListener("voice:conversation_update", handleConversationUpdate);
            window.removeEventListener("voice:client-created", clearInteractiveState);
            window.removeEventListener("voice:invoice-created", clearInteractiveState);
            window.removeEventListener("voice:expense-created", clearInteractiveState);
        };
    }, []);

    const missingKeyIssues = providerPopup.issues.filter((issue) => issue.status === "missing_api_key");
    const limitIssues = providerPopup.issues.filter((issue) => issue.status === "limit_reached");
    const otherProviderIssues = providerPopup.issues.filter(
        (issue) => issue.status !== "missing_api_key" && issue.status !== "limit_reached"
    );

    // Collapsed pill button when hidden
    if (!isVisible) {
        return (
            <motion.button
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                className="fixed bottom-6 right-6 rounded-full h-14 w-14 shadow-2xl z-50 flex items-center justify-center transition-all hover:scale-105"
                style={{ backgroundColor: "#4CBB17", color: "#000", boxShadow: "0 0 24px rgba(0,255,178,0.4)" }}
                onClick={() => setIsVisible(true)}
                aria-label="Open Voice Agent"
            >
                <Phone className="h-6 w-6" />
            </motion.button>
        );
    }

    return (
        <>
            <motion.div
                key="voice-panel"
                initial={{ opacity: 0, y: 24, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 24, scale: 0.96 }}
                transition={{ type: "spring", bounce: 0.2, duration: 0.4 }}
                className="fixed bottom-6 right-6 w-[300px] shadow-2xl z-50 rounded-2xl overflow-hidden"
                style={{
                    backgroundColor: "var(--voice-bg, #111111)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    backdropFilter: "blur(20px)",
                    boxShadow: isConnect
                        ? "0 0 0 1px rgba(0,255,178,0.25), 0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(0,255,178,0.08)"
                        : "0 20px 60px rgba(0,0,0,0.5)",
                }}
            >
                {/* Header */}
                <div
                    className="flex items-center justify-between px-4 py-3"
                    style={{ borderBottom: "1px solid rgba(255,255,255,0.07)" }}
                >
                    <div className="flex items-center gap-2">
                        {/* Live indicator */}
                        {isConnect ? (
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#4CBB17] opacity-75" />
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-[#4CBB17]" />
                            </span>
                        ) : (
                            <span className="h-2 w-2 rounded-full bg-white/20" />
                        )}
                        <span className="text-sm font-semibold text-white">Voice Agent</span>
                        <span
                            className="text-xs px-1.5 py-0.5 rounded-md font-medium"
                            style={{ backgroundColor: "rgba(255,255,255,0.07)", color: "rgba(255,255,255,0.4)" }}
                        >
                            {agentType}
                        </span>
                    </div>
                    <button
                        className="p-1 rounded-lg transition-colors"
                        style={{ color: "rgba(255,255,255,0.3)" }}
                        onMouseEnter={e => e.currentTarget.style.color = "#fff"}
                        onMouseLeave={e => e.currentTarget.style.color = "rgba(255,255,255,0.3)"}
                        onClick={() => setIsVisible(false)}
                        aria-label="Minimise voice agent"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-5">
                    {token ? (
                        <LiveKitRoom
                            token={token}
                            serverUrl={url}
                            connect={isConnect}
                            audio={true}
                            video={false}
                            onDisconnected={disconnect}
                            data-lk-theme="default"
                            style={{ height: "100%" }}
                        >
                            <AgentContent onDisconnect={disconnect} />
                            <RoomAudioRenderer />
                        </LiveKitRoom>
                    ) : (
                        /* Idle / pre-connect state */
                        <div className="flex flex-col items-center gap-5 py-2">
                            <AIVoiceInput
                                isActive={false}
                                isConnecting={isProcessing}
                                onToggle={isLoaded && user?.id && !onboardingLoading ? startCall : undefined}
                            />
                            {(!isLoaded || !user?.id) && (
                                <p className="text-xs text-center" style={{ color: "rgba(255,255,255,0.3)" }}>
                                    Sign in to start a voice session
                                </p>
                            )}
                        </div>
                    )}

                    {activeClientPicker && (
                        <div
                            className="mt-4 rounded-xl border border-white/10 p-3"
                            style={{ backgroundColor: "rgba(255,255,255,0.03)" }}
                        >
                            <p className="text-sm font-semibold text-white">{activeClientPicker.title || "Select Client"}</p>
                            <p className="text-xs mt-1 mb-3" style={{ color: "rgba(255,255,255,0.55)" }}>
                                {activeClientPicker.message || "Choose a client or keep speaking."}
                            </p>
                            <div className="max-h-40 overflow-y-auto flex flex-col gap-2">
                                {(activeClientPicker.clients || []).map((client, index) => (
                                    <button
                                        key={buildStableKey("voice-client", client.id, client.name, index)}
                                        disabled={isInputLocked}  // ── DISABLE WHILE PROCESSING
                                        className="w-full text-left rounded-lg px-3 py-2 text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                                        style={{
                                            backgroundColor: isInputLocked ? "rgba(255,255,255,0.02)" : "rgba(255,255,255,0.05)",
                                            color: isInputLocked ? "rgba(255,255,255,0.4)" : "#fff",
                                            border: "1px solid rgba(255,255,255,0.08)",
                                        }}
                                        onClick={() => handleClientPick(client)}
                                    >
                                        {client.name}
                                        {isInputLocked && <span className="text-xs ml-2">⏳</span>}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

            </motion.div>
            
            <AnimatePresence>
                {activeDialog && (
                    <ClientInputDialog 
                        key={buildStableKey("voice-dialog", activeDialog.dialog_id, activeDialog.session_id, activeDialog.title)}
                        dialog={activeDialog}
                        onSubmit={(result) => {
                            if (result?.message) {
                                const notify = result?.success === false ? toast.error : toast.success;
                                notify(result.message);
                            }
                            setActiveClientPicker(null);
                        }}
                        onClose={() => setActiveDialog(null)}
                    />
                )}
            </AnimatePresence>

            <Dialog
                open={providerPopup.open}
                onOpenChange={(open) => setProviderPopup((current) => ({ ...current, open }))}
            >
                <DialogContent className="border-[#2A2A2A] bg-[#111111] text-white sm:max-w-lg">
                    <DialogHeader>
                        <DialogTitle>
                            {providerPopup.blocking ? "Voice Agent Setup Needed" : "Voice Provider Warning"}
                        </DialogTitle>
                        <DialogDescription className="text-[#A0A0A0]">
                            {providerPopup.message || (
                                providerPopup.blocking
                                    ? "The voice agent cannot start until the blocking provider issues below are fixed."
                                    : "The voice agent can continue, but some provider settings need attention."
                            )}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-3">
                        {missingKeyIssues.length > 0 && (
                            <div className="rounded-xl border border-[#2A2A2A] bg-black/20 p-3">
                                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#F5C35B]">
                                    Empty API Keys
                                </p>
                                <div className="mt-3 space-y-2">
                                    {missingKeyIssues.map((issue, index) => (
                                        <div key={buildStableKey("provider-missing", issue.provider, issue.env_var, issue.status, index)} className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                                            <div className="flex items-center justify-between gap-3">
                                                <span className="text-sm font-semibold text-white">{issue.provider}</span>
                                                <span className="text-[10px] uppercase tracking-[0.18em] text-[#A0A0A0]">
                                                    {issue.env_var}
                                                </span>
                                            </div>
                                            <p className="mt-2 text-sm text-[#D0D0D0]">{issue.message}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {limitIssues.length > 0 && (
                            <div className="rounded-xl border border-[#2A2A2A] bg-black/20 p-3">
                                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#FF7A7A]">
                                    Limits Reached
                                </p>
                                <div className="mt-3 space-y-2">
                                    {limitIssues.map((issue, index) => (
                                        <div key={buildStableKey("provider-limit", issue.provider, issue.env_var, issue.status, index)} className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                                            <div className="flex items-center justify-between gap-3">
                                                <span className="text-sm font-semibold text-white">{issue.provider}</span>
                                                <span className="text-[10px] uppercase tracking-[0.18em] text-[#A0A0A0]">
                                                    {PROVIDER_STATUS_LABELS[issue.status] || issue.status}
                                                </span>
                                            </div>
                                            <p className="mt-2 text-sm text-[#D0D0D0]">{issue.message}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {otherProviderIssues.length > 0 && (
                            <div className="rounded-xl border border-[#2A2A2A] bg-black/20 p-3">
                                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#8DC9FF]">
                                    Other Provider Issues
                                </p>
                                <div className="mt-3 space-y-2">
                                    {otherProviderIssues.map((issue, index) => (
                                        <div key={buildStableKey("provider-other", issue.provider, issue.env_var, issue.status, index)} className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                                            <div className="flex items-center justify-between gap-3">
                                                <span className="text-sm font-semibold text-white">{issue.provider}</span>
                                                <span className="text-[10px] uppercase tracking-[0.18em] text-[#A0A0A0]">
                                                    {PROVIDER_STATUS_LABELS[issue.status] || issue.status}
                                                </span>
                                            </div>
                                            <p className="mt-2 text-sm text-[#D0D0D0]">{issue.message}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    <DialogFooter>
                        <Button
                            type="button"
                            className="bg-white text-black hover:bg-white/90"
                            onClick={() => setProviderPopup((current) => ({ ...current, open: false }))}
                        >
                            {providerPopup.blocking ? "Close" : "Continue"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}

function AgentContent({ onDisconnect }) {
    useVoiceEvents();
    const { state } = useConnectionState();
    const isConnected = state === ConnectionState.Connected;
    const isConnecting = state === ConnectionState.Connecting;
    const isDisconnected = state === ConnectionState.Disconnected || state === ConnectionState.Reconnecting;

    // ── Transcript feed ─────────────────────────────────────
    const room = useRoomContext();
    const [transcript, setTranscript] = useState([]);
    const transcriptEndRef = useRef(null);

    useEffect(() => {
        if (!room) return;
        const handler = (segments, participant) => {
            const finalSegments = segments.filter(s => s.final && s.text?.trim());
            if (!finalSegments.length) return;
            // Local participant = user speech; remote/agent = agent speech
            const isUserSpeech = participant?.isLocal === true;
            setTranscript(prev => [
                ...prev.slice(-20), // keep last 20 lines to avoid overflow
                ...finalSegments.map(s => ({
                    id: s.id,
                    role: isUserSpeech ? "user" : "agent",
                    text: s.text.trim(),
                }))
            ]);
        };
        room.on("transcriptionReceived", handler);
        return () => room.off("transcriptionReceived", handler);
    }, [room]);

    useEffect(() => {
        const speakManualResponse = (event) => {
            const responseText = event?.detail?.responseText?.trim();
            if (!responseText) return;

            setTranscript((prev) => [
                ...prev.slice(-20),
                {
                    id: `manual-${Date.now()}`,
                    role: "agent",
                    text: responseText,
                },
            ]);

            if (typeof window !== "undefined" && "speechSynthesis" in window) {
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(responseText);
                utterance.rate = 1;
                utterance.pitch = 1;
                utterance.volume = 1;
                window.speechSynthesis.speak(utterance);
            }
        };

        window.addEventListener("voice:manual_agent_response", speakManualResponse);
        return () => window.removeEventListener("voice:manual_agent_response", speakManualResponse);
    }, []);

    // Auto-scroll transcript to bottom
    useEffect(() => {
        transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [transcript]);

    // Single exclusive status label
    const statusLabel = isConnecting
        ? { text: "Connecting to room…", color: "#FFB300" }
        : isConnected
            ? { text: "Connected · Listening", color: "#4CBB17" }
            : isDisconnected
                ? { text: "Disconnected", color: "#CD1C18" }
                : null;

    return (
        <div className="flex flex-col gap-3">
            {/* ── Status — exactly one label at a time ── */}
            <div className="text-center h-5">
                {statusLabel && (
                    <p
                        className={isConnecting ? "text-xs animate-pulse" : "text-xs"}
                        style={{ color: statusLabel.color }}
                    >
                        {statusLabel.text}
                    </p>
                )}
            </div>

            {/* Voice visualizer */}
            <AIVoiceInput
                isActive={isConnected}
                isConnecting={isConnecting}
                onToggle={onDisconnect}
            />

            {/* ── Transcript feed ── */}
            {(transcript.length > 0 || isConnected) && (
                <div
                    className="mx-3 rounded-xl overflow-hidden"
                    style={{
                        backgroundColor: "rgba(255,255,255,0.03)",
                        border: "1px solid rgba(255,255,255,0.06)",
                    }}
                >
                    <div
                        className="px-3 py-1.5 flex items-center gap-1.5"
                        style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}
                    >
                        <span className="text-[9px] font-semibold uppercase tracking-widest" style={{ color: "rgba(255,255,255,0.25)" }}>
                            Transcript
                        </span>
                    </div>
                    <div
                        className="flex flex-col gap-1.5 px-3 py-2 overflow-y-auto"
                        style={{ maxHeight: "110px", scrollbarWidth: "none" }}
                    >
                        {transcript.length === 0 ? (
                            <p className="text-[10px] text-center py-1" style={{ color: "rgba(255,255,255,0.18)" }}>
                                Transcript will appear here…
                            </p>
                        ) : (
                            transcript.map((entry, index) => (
                                <div
                                    key={buildStableKey("voice-transcript", entry.id, entry.role, entry.text.slice(0, 24), index)}
                                    className={`flex gap-1.5 ${entry.role === "user" ? "justify-end" : "justify-start"}`}
                                >
                                    <div
                                        className="max-w-[85%] rounded-lg px-2.5 py-1 text-[10px] leading-relaxed"
                                        style={
                                            entry.role === "user"
                                                ? {
                                                    backgroundColor: "rgba(76,187,23,0.15)",
                                                    color: "rgba(255,255,255,0.75)",
                                                    borderRadius: "10px 10px 2px 10px",
                                                }
                                                : {
                                                    backgroundColor: "rgba(255,255,255,0.06)",
                                                    color: "rgba(255,255,255,0.55)",
                                                    borderRadius: "10px 10px 10px 2px",
                                                }
                                        }
                                    >
                                        {entry.text}
                                    </div>
                                </div>
                            ))
                        )}
                        <div ref={transcriptEndRef} />
                    </div>
                </div>
            )}

            {/* End call button */}
            <div className="flex justify-center px-3">
                <button
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all hover:opacity-90"
                    style={{
                        backgroundColor: "rgba(255, 68, 68, 0.15)",
                        color: "#CD1C18",
                        border: "1px solid rgba(255, 68, 68, 0.3)",
                    }}
                    onClick={onDisconnect}
                >
                    <PhoneOff className="h-4 w-4" />
                    End Call
                </button>
            </div>

            <p className="text-center text-[9px] pb-2" style={{ color: "rgba(255,255,255,0.15)" }}>
                Powered by LiveKit
            </p>
        </div>
    );
}
