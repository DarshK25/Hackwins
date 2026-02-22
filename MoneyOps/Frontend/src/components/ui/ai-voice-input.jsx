import { Mic } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

/**
 * AIVoiceInput — styled waveform visualizer button
 *
 * Props:
 *  isActive        boolean   — controlled: is the mic currently recording?
 *  onToggle        fn        — called when the button is clicked
 *  isConnecting    boolean   — shows a connecting spinner state
 *  visualizerBars  number    — how many bars in the waveform (default 40)
 *  className       string
 */
export function AIVoiceInput({
    isActive = false,
    onToggle,
    isConnecting = false,
    visualizerBars = 40,
    className,
}) {
    const [time, setTime] = useState(0);
    const [isClient, setIsClient] = useState(false);
    const barsRef = useRef([]);

    useEffect(() => { setIsClient(true); }, []);

    // Timer
    useEffect(() => {
        let id;
        if (isActive) {
            id = setInterval(() => setTime(t => t + 1), 1000);
        } else {
            setTime(0);
        }
        return () => clearInterval(id);
    }, [isActive]);

    // Pre-generate random heights once per activation so they don't re-randomize on every render
    useEffect(() => {
        if (isActive && isClient) {
            barsRef.current = Array.from({ length: visualizerBars }, () => 15 + Math.random() * 85);
        }
    }, [isActive, isClient, visualizerBars]);

    const formatTime = (s) => {
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
    };

    return (
        <div className={cn("flex flex-col items-center gap-3 w-full", className)}>
            {/* Waveform bars */}
            <div className="h-10 w-full flex items-center justify-center gap-[2px] px-2">
                {isClient && Array.from({ length: visualizerBars }).map((_, i) => (
                    <div
                        key={i}
                        className="rounded-full flex-shrink-0 transition-all"
                        style={{
                            width: "2px",
                            height: isActive
                                ? `${barsRef.current[i] ?? 30}%`
                                : "4px",
                            backgroundColor: isActive
                                ? `rgba(0, 255, 178, ${0.4 + (i % 3) * 0.2})`
                                : "rgba(255,255,255,0.12)",
                            animationName: isActive ? "voicePulse" : "none",
                            animationDuration: `${0.6 + (i % 5) * 0.15}s`,
                            animationTimingFunction: "ease-in-out",
                            animationIterationCount: "infinite",
                            animationDirection: "alternate",
                            animationDelay: `${(i % 7) * 0.08}s`,
                        }}
                    />
                ))}
            </div>

            {/* Mic button */}
            <button
                onClick={onToggle}
                disabled={isConnecting}
                className={cn(
                    "relative h-14 w-14 rounded-2xl flex items-center justify-center transition-all duration-300 outline-none",
                    isActive
                        ? "scale-110"
                        : "hover:scale-105",
                    isConnecting && "opacity-60 cursor-not-allowed"
                )}
                style={
                    isActive
                        ? {
                            backgroundColor: "#4CBB17",
                            boxShadow: "0 0 0 4px rgba(0,255,178,0.2), 0 0 24px rgba(0,255,178,0.35)",
                            color: "#000",
                        }
                        : {
                            backgroundColor: "rgba(255,255,255,0.06)",
                            border: "1px solid rgba(255,255,255,0.12)",
                            color: "rgba(255,255,255,0.5)",
                        }
                }
                aria-label={isActive ? "Stop recording" : "Start recording"}
            >
                {isConnecting ? (
                    <div
                        className="h-5 w-5 rounded-sm"
                        style={{
                            animation: "spin 3s linear infinite",
                            backgroundColor: "rgba(255,255,255,0.7)",
                        }}
                    />
                ) : isActive ? (
                    /* Stop icon — filled square */
                    <div className="h-5 w-5 rounded-sm" style={{ backgroundColor: "#000" }} />
                ) : (
                    <Mic className="h-5 w-5" />
                )}

                {/* Pulsing ring when active */}
                {isActive && (
                    <span
                        className="absolute inset-0 rounded-2xl"
                        style={{
                            animation: "voiceRing 1.5s ease-out infinite",
                            border: "2px solid rgba(0,255,178,0.5)",
                        }}
                    />
                )}
            </button>

            {/* Timer + label */}
            <div className="flex flex-col items-center gap-0.5">
                <span
                    className="font-mono text-sm tabular-nums"
                    style={{ color: isActive ? "#4CBB17" : "rgba(255,255,255,0.3)" }}
                >
                    {formatTime(time)}
                </span>
                <span
                    className="text-xs"
                    style={{ color: isActive ? "rgba(255,255,255,0.6)" : "rgba(255,255,255,0.25)" }}
                >
                    {isConnecting ? "Connecting…" : isActive ? "Listening" : "Click to speak"}
                </span>
            </div>
        </div>
    );
}
