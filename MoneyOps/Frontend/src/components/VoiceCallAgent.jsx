import { useState, useCallback, useEffect, useRef } from "react";
import { useUser } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";
import { X, Phone, PhoneOff, Mic, Loader2 } from "lucide-react";
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

export function VoiceCallAgent({ agentType = "orchestrator" }) {
    const { user, isLoaded } = useUser();
    const [isVisible, setIsVisible] = useState(true);
    const [token, setToken] = useState("");
    const [url, setUrl] = useState("");
    const [isConnect, setIsConnect] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);

    const startCall = async () => {
        if (!user?.id) {
            toast.error("Please sign in to start a voice call.");
            return;
        }
        setIsProcessing(true);
        try {
            const userId = user.id;
            const sessionToken = await window.Clerk?.session?.getToken();
            const orgId = user.organizationMemberships?.[0]?.organization?.id || userId;
            const metadata = JSON.stringify({
                user_id: userId,
                org_id: orgId,
                user_name: user.fullName || user.username || "User",
                auth_token: sessionToken || "",
            });
            const params = new URLSearchParams({ user_id: userId, org_id: orgId, metadata });
            const res = await fetch(`/api/v1/voice/token?${params.toString()}`);
            if (!res.ok) {
                const errText = await res.text();
                throw new Error(errText || `Failed to fetch token (${res.status})`);
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
    }, []);

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
        <AnimatePresence>
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
                                onToggle={isLoaded && user?.id ? startCall : undefined}
                            />
                            {(!isLoaded || !user?.id) && (
                                <p className="text-xs text-center" style={{ color: "rgba(255,255,255,0.3)" }}>
                                    Sign in to start a voice session
                                </p>
                            )}
                        </div>
                    )}
                </div>
            </motion.div>
        </AnimatePresence>
    );
}

function AgentContent({ onDisconnect }) {
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
                            transcript.map((entry) => (
                                <div
                                    key={entry.id}
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
