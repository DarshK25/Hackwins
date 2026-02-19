import { useState, useCallback } from "react";
import { useUser } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, X, Phone, PhoneOff, Mic } from "lucide-react";
import { toast } from "sonner";
import {
    LiveKitRoom,
    RoomAudioRenderer,
    useConnectionState,
    ConnectionState,
} from "@livekit/components-react";
import "@livekit/components-styles";

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
            // Use Clerk user ID for LiveKit token (backend/API Gateway auth unchanged)
            const userId = user.id;

            // Fetch token from AI Gateway (proxied via Vite: /api/v1 -> localhost:8001)
            const res = await fetch(`/api/v1/voice/token?user_id=${userId}`);

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
            if (!data.token || !data.url) {
                throw new Error("Invalid token response: missing token or url");
            }

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

    if (!isVisible) {
        return (
            <Button
                className="fixed bottom-4 right-4 rounded-full h-14 w-14 shadow-xl z-50 bg-green-600 hover:bg-green-700 animate-in zoom-in slide-in-from-bottom-4"
                onClick={() => setIsVisible(true)}
            >
                <Phone className="h-6 w-6" />
            </Button>
        );
    }

    return (
        <Card className="fixed bottom-4 right-4 w-80 shadow-xl border-primary/20 z-50 backdrop-blur-sm bg-background/95 animate-in slide-in-from-bottom-10 fade-in duration-300">
            <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    {isConnect ? (
                        <span className="relative flex h-3 w-3">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                        </span>
                    ) : (
                        <span className="relative inline-flex rounded-full h-3 w-3 bg-slate-300"></span>
                    )}
                    Voice Agent ({agentType})
                </CardTitle>
                <div className="flex items-center gap-1">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => setIsVisible(false)}
                    >
                        <X className="h-3 w-3" />
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
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
                    <div className="flex flex-col items-center justify-center space-y-4 py-4">
                        <div className="h-16 w-16 rounded-full bg-slate-100 flex items-center justify-center">
                            <Mic className="h-8 w-8 text-slate-400" />
                        </div>
                        <p className="text-xs text-slate-500 text-center">
                            Connect to speak with the {agentType} agent.
                        </p>
                        <Button
                            onClick={startCall}
                            disabled={isProcessing || !isLoaded || !user?.id}
                            className="w-full bg-green-600 hover:bg-green-700"
                        >
                            {isProcessing ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Connecting...
                                </>
                            ) : (
                                <>
                                    <Phone className="mr-2 h-4 w-4" /> Start Call
                                </>
                            )}
                        </Button>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

function AgentContent({ onDisconnect }) {
    const { state } = useConnectionState();

    return (
        <div className="flex flex-col space-y-4">
            {/* Status Display */}
            <div className="text-center py-2 h-6">
                {state === ConnectionState.Connecting && (
                    <p className="text-xs text-yellow-600 animate-pulse">Connecting to room...</p>
                )}
                {state === ConnectionState.Connected && (
                    <p className="text-xs text-green-600">Connected. Listening...</p>
                )}
                {(state === ConnectionState.Disconnected || state === ConnectionState.Reconnecting) && (
                    <p className="text-xs text-red-500">Disconnected</p>
                )}
            </div>

            {/* Visualizer Placeholder */}
            <div className="h-16 bg-slate-50 rounded-lg flex items-center justify-center overflow-hidden relative">
                {state === ConnectionState.Connected ? (
                    <div className="flex items-center gap-1 h-8 items-end">
                        <div className="w-1 bg-green-500 animate-[pulse_1s_ease-in-out_infinite]" style={{ height: '40%', animationDelay: '0ms' }}></div>
                        <div className="w-1 bg-green-500 animate-[pulse_1.2s_ease-in-out_infinite]" style={{ height: '70%', animationDelay: '100ms' }}></div>
                        <div className="w-1 bg-green-500 animate-[pulse_0.8s_ease-in-out_infinite]" style={{ height: '30%', animationDelay: '200ms' }}></div>
                        <div className="w-1 bg-green-500 animate-[pulse_1.1s_ease-in-out_infinite]" style={{ height: '60%', animationDelay: '300ms' }}></div>
                        <div className="w-1 bg-green-500 animate-[pulse_0.9s_ease-in-out_infinite]" style={{ height: '50%', animationDelay: '400ms' }}></div>
                    </div>
                ) : (
                    <div className="text-slate-300 text-xs">Waveform</div>
                )}
            </div>

            {/* Controls */}
            <div className="flex justify-center gap-4 pt-2">
                <Button
                    variant="destructive"
                    size="icon"
                    className="h-12 w-12 rounded-full shadow-lg hover:scale-105 transition-transform"
                    onClick={onDisconnect}
                >
                    <PhoneOff className="h-5 w-5" />
                </Button>
            </div>

            <div className="text-center pt-2">
                <p className="text-[10px] text-slate-400">Powered by LiveKit</p>
            </div>
        </div>
    );
}
