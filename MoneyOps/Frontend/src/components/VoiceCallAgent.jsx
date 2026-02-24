import { useState, useCallback, useRef } from "react";
import { useUser } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, X, Phone, PhoneOff, Mic, ChevronDown, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import {
    LiveKitRoom,
    RoomAudioRenderer,
    useConnectionState,
    ConnectionState,
    useDataChannel,
} from "@livekit/components-react";
import "@livekit/components-styles";

// Vite proxy routes /api/v1 → http://localhost:8001 (AI Gateway)
const VOICE_BASE = "/api/v1/voice";

export function VoiceCallAgent({ agentType = "orchestrator", onActionExec }) {
    const { user, isLoaded } = useUser();
    const { orgId, userId: mongoUserId } = useOnboardingStatus();

    const [isVisible, setIsVisible] = useState(true);
    const [isMinimised, setIsMinimised] = useState(false);
    const [token, setToken] = useState("");
    const [url, setUrl] = useState("");
    const [roomName, setRoomName] = useState("");
    const [isConnect, setIsConnect] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [liveKitUnavailable, setLiveKitUnavailable] = useState(false);

    // Live conversation transcript shown in the card
    const [transcript, setTranscript] = useState([]);
    const [lastAction, setLastAction] = useState(null); // { type, message }
    const sessionIdRef = useRef(null);
    const transcriptEndRef = useRef(null);

    // ── Start call ────────────────────────────────────────────────────────────
    const startCall = async () => {
        if (!user?.id) { toast.error("Please sign in first."); return; }
        if (!orgId) { toast.error("Organisation not loaded yet. Please wait."); return; }

        setIsProcessing(true);
        setTranscript([]);
        setLastAction(null);
        sessionIdRef.current = crypto.randomUUID();

        try {
            const params = new URLSearchParams({
                user_id: mongoUserId || user.id,
                org_id: orgId,
            });
            const res = await fetch(`${VOICE_BASE}/token?${params}`);

            if (res.status === 503 || res.status === 500) {
                setLiveKitUnavailable(true);
                setIsProcessing(false);
                return;
            }
            if (!res.ok) throw new Error(`Token fetch failed (${res.status})`);

            const contentType = res.headers.get("content-type");
            if (!contentType?.includes("application/json")) {
                throw new Error("AI Gateway is not returning JSON. Is it running on port 8001?");
            }

            const data = await res.json();
            if (!data.token || !data.url) throw new Error("Invalid token response");

            setToken(data.token);
            setUrl(data.url);
            setRoomName(data.room_name || "");
            setIsConnect(true);
            setIsMinimised(false);
        } catch (error) {
            console.error("Failed to start call:", error);
            toast.error("Could not connect to voice agent. Check AI Gateway on port 8001.");
        } finally {
            setIsProcessing(false);
        }
    };

    const disconnect = useCallback(() => {
        setIsConnect(false);
        setToken("");
        setIsProcessing(false);
    }, []);

    // ── Called by AgentContent when a voice round-trip completes ─────────────
    const handleGatewayResult = useCallback(
        async (userText) => {
            if (!userText?.trim()) return;

            // Add user turn to transcript immediately
            setTranscript((prev) => [
                ...prev,
                { role: "user", text: userText, ts: Date.now() },
            ]);

            try {
                const res = await fetch(`${VOICE_BASE}/process`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        text: userText,
                        user_id: mongoUserId || user?.id || "unknown",
                        org_id: orgId || "default_org",
                        session_id: sessionIdRef.current || crypto.randomUUID(),
                        conversation_history: [],
                    }),
                });

                if (!res.ok) return;
                const data = await res.json();

                // Add assistant turn
                setTranscript((prev) => [
                    ...prev,
                    { role: "assistant", text: data.response_text, ts: Date.now() },
                ]);

                // If an invoice was created, show a success badge and notify parent
                if (data.action_result?.status === "created" && !data.needs_more_info) {
                    setLastAction({
                        type: "invoice_created",
                        message: data.response_text,
                        data: data.action_result,
                    });
                    toast.success(
                        `✅ ${data.response_text}`,
                        { duration: 6000, description: "Invoice saved to MongoDB" }
                    );
                    // Notify parent page (e.g. InvoicesPage) to refresh
                    onInvoiceCreated?.();
                }

                // Scroll to bottom of transcript
                setTimeout(() => transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
            } catch (err) {
                console.error("Gateway call failed:", err);
            }
        },
        [mongoUserId, orgId, user?.id, onActionExec]
    );

    // ── Collapsed / invisible states ──────────────────────────────────────────
    if (!isVisible) {
        return (
            <Button
                id="voice-agent-bubble"
                className="fixed bottom-4 right-4 rounded-full h-14 w-14 shadow-xl z-50 bg-green-600 hover:bg-green-700 animate-in zoom-in"
                onClick={() => setIsVisible(true)}
                title="Open Voice Agent"
            >
                <Phone className="h-6 w-6" />
            </Button>
        );
    }

    return (
        <Card
            id="voice-agent-card"
            className="fixed bottom-4 right-4 w-80 shadow-2xl border-green-200/40 z-50 backdrop-blur-sm bg-background/95 animate-in slide-in-from-bottom-10 fade-in duration-300"
        >
            {/* ── Header ────────────────────────────────────────────────────── */}
            <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    {isConnect ? (
                        <span className="relative flex h-3 w-3">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500" />
                        </span>
                    ) : (
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-slate-300" />
                    )}
                    <span className="bg-gradient-to-r from-green-600 to-emerald-500 bg-clip-text text-transparent">
                        MoneyOps AI
                    </span>
                </CardTitle>

                <div className="flex items-center gap-1">
                    {isConnect && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => setIsMinimised((v) => !v)}
                            title={isMinimised ? "Expand" : "Minimise"}
                        >
                            <ChevronDown
                                className={`h-3 w-3 transition-transform ${isMinimised ? "rotate-180" : ""}`}
                            />
                        </Button>
                    )}
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => setIsVisible(false)}
                        title="Hide"
                    >
                        <X className="h-3 w-3" />
                    </Button>
                </div>
            </CardHeader>

            {/* ── Content ───────────────────────────────────────────────────── */}
            {!isMinimised && (
                <CardContent className="space-y-3">
                    {token ? (
                        <LiveKitRoom
                            token={token}
                            serverUrl={url}
                            connect={isConnect}
                            audio={true}
                            video={false}
                            onDisconnected={disconnect}
                            data-lk-theme="default"
                        >
                            <AgentContent
                                onDisconnect={disconnect}
                                onData={({ user_text, response_text, action_result, needs_more_info, intent }) => {
                                    // 1. Update Transcript
                                    if (user_text) {
                                        setTranscript(prev => [...prev, { role: "user", text: user_text, ts: Date.now() }]);
                                    }
                                    if (response_text) {
                                        setTranscript(prev => [...prev, { role: "assistant", text: response_text, ts: Date.now() }]);
                                        // Scroll to bottom
                                        setTimeout(() => transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
                                    }

                                    // 2. Handle Actions
                                    if (action_result?.status === "created" && !needs_more_info) {
                                        const actionType = intent === "CLIENT_CREATE" ? "client_created" : "invoice_created";

                                        setLastAction({
                                            type: actionType,
                                            message: response_text,
                                            data: action_result,
                                        });
                                        toast.success(`✅ ${response_text}`);
                                        onActionExec?.({ type: actionType, data: action_result });
                                    }
                                }}
                            />
                            <RoomAudioRenderer />
                        </LiveKitRoom>
                    ) : (
                        <IdleContent
                            isProcessing={isProcessing}
                            isLoaded={isLoaded}
                            user={user}
                            liveKitUnavailable={liveKitUnavailable}
                            onStart={startCall}
                        />
                    )}

                    {/* ── Live Transcript ──────────────────────────────────── */}
                    {transcript.length > 0 && (
                        <div className="max-h-36 overflow-y-auto rounded-lg bg-slate-50 dark:bg-slate-900 p-2 space-y-1 text-xs border">
                            {transcript.map((msg, i) => (
                                <div
                                    key={i}
                                    className={`flex gap-1 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                                >
                                    <span
                                        className={`px-2 py-1 rounded-lg max-w-[88%] leading-snug ${msg.role === "user"
                                            ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200"
                                            : "bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border"
                                            }`}
                                    >
                                        {msg.text}
                                    </span>
                                </div>
                            ))}
                            <div ref={transcriptEndRef} />
                        </div>
                    )}

                    {/* ── Last Action Badge ────────────────────────────────── */}
                    {lastAction && (
                        <div
                            id="voice-action-created-badge"
                            className="flex items-start gap-2 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-2 text-xs animate-in fade-in slide-in-from-bottom-2"
                        >
                            <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
                            <div>
                                <p className="font-medium text-green-700 dark:text-green-300">
                                    {lastAction.type === "client_created" ? "Client Created" : "Invoice Created"}
                                </p>
                                <p className="text-green-600 dark:text-green-400 mt-0.5">
                                    {lastAction.message}
                                </p>
                            </div>
                        </div>
                    )}

                    {/* ── Hint ─────────────────────────────────────────────── */}
                    {!isConnect && !liveKitUnavailable && (
                        <p className="text-[10px] text-slate-400 text-center">
                            Try: <em>"Create an invoice for Tanoosh for ₹10,000"</em>
                        </p>
                    )}
                </CardContent>
            )}
        </Card>
    );
}


// ── Idle (pre-connect) content ────────────────────────────────────────────────
function IdleContent({ isProcessing, isLoaded, user, liveKitUnavailable, onStart }) {
    if (liveKitUnavailable) {
        return (
            <div className="flex flex-col items-center space-y-3 py-2">
                <div className="h-14 w-14 rounded-full bg-amber-50 flex items-center justify-center">
                    <Mic className="h-7 w-7 text-amber-400" />
                </div>
                <p className="text-xs text-slate-500 text-center">
                    Voice calls require LiveKit configuration.
                </p>
                <p className="text-[10px] text-slate-400 text-center">
                    Add <code className="bg-slate-100 px-1 rounded">LIVEKIT_API_KEY</code>,{" "}
                    <code className="bg-slate-100 px-1 rounded">LIVEKIT_API_SECRET</code> and{" "}
                    <code className="bg-slate-100 px-1 rounded">LIVEKIT_URL</code> to your AI Gateway{" "}
                    <code className="bg-slate-100 px-1 rounded">.env</code>
                </p>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center space-y-3 py-2">
            {/* Animated mic icon */}
            <div className="relative h-16 w-16">
                <div className="absolute inset-0 rounded-full bg-green-100 dark:bg-green-900/30 animate-ping opacity-30" />
                <div className="relative h-16 w-16 rounded-full bg-gradient-to-br from-green-50 to-emerald-100 dark:from-green-900/40 dark:to-emerald-900/20 flex items-center justify-center shadow-md">
                    <Mic className="h-8 w-8 text-green-600" />
                </div>
            </div>
            <p className="text-xs text-slate-500 text-center">
                Click to speak with your AI financial assistant.
            </p>
            <Button
                id="voice-start-call-btn"
                onClick={onStart}
                disabled={isProcessing || !isLoaded || !user?.id}
                className="w-full bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-700 hover:to-emerald-600 text-white shadow-md"
            >
                {isProcessing ? (
                    <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Connecting...
                    </>
                ) : (
                    <>
                        <Phone className="mr-2 h-4 w-4" /> Start Voice Call
                    </>
                )}
            </Button>
        </div>
    );
}


// ── Active connection content ─────────────────────────────────────────────────
function AgentContent({ onDisconnect, onData }) {
    const { state } = useConnectionState();
    const connected = state === ConnectionState.Connected;

    // Listen for data from the voice-service (AI Gateway results)
    useDataChannel("gateway_results", (message) => {
        try {
            const data = JSON.parse(new TextDecoder().decode(message.payload));
            if (data.type === "conversation_update") {
                onData(data);
            }
        } catch (err) {
            console.error("Failed to parse data message:", err);
        }
    });

    return (
        <div className="flex flex-col space-y-3">
            {/* Status line */}
            <div className="text-center py-1">
                {state === ConnectionState.Connecting && (
                    <p className="text-xs text-yellow-600 animate-pulse">Connecting to room…</p>
                )}
                {connected && (
                    <p className="text-xs text-green-600 font-medium">🎙 Listening…</p>
                )}
                {(state === ConnectionState.Disconnected || state === ConnectionState.Reconnecting) && (
                    <p className="text-xs text-red-500">Disconnected</p>
                )}
            </div>

            {/* Animated waveform */}
            <div className="h-14 bg-gradient-to-b from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 rounded-xl flex items-center justify-center overflow-hidden">
                {connected ? (
                    <div className="flex items-end gap-1 h-8">
                        {[40, 70, 30, 60, 50, 80, 35, 65, 45, 75].map((h, i) => (
                            <div
                                key={i}
                                className="w-1 bg-gradient-to-t from-green-600 to-emerald-400 rounded-full"
                                style={{
                                    height: `${h}%`,
                                    animation: `pulse ${0.7 + i * 0.1}s ease-in-out infinite alternate`,
                                    animationDelay: `${i * 60}ms`,
                                }}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="text-slate-300 text-xs">Waveform</div>
                )}
            </div>

            {/* Hang-up button */}
            <div className="flex justify-center">
                <Button
                    id="voice-hangup-btn"
                    variant="destructive"
                    size="icon"
                    className="h-11 w-11 rounded-full shadow-lg hover:scale-105 transition-transform"
                    onClick={onDisconnect}
                    title="End Call"
                >
                    <PhoneOff className="h-5 w-5" />
                </Button>
            </div>

            <p className="text-[10px] text-slate-400 text-center">Powered by LiveKit + Groq</p>
        </div>
    );
}
