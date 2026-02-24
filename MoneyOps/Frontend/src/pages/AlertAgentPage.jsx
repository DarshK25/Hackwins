import { useState, useEffect } from "react";
import {
    Bell,
    AlertTriangle,
    CheckCircle,
    XCircle,
    Clock,
    Send,
    Loader2,
} from "lucide-react";

const SEVERITY_STYLES = {
    critical: {
        border: "#CD1C1840",
        bg: "#CD1C1810",
        text: "#CD1C18",
        label: "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]",
    },
    high: {
        border: "#FF8C0040",
        bg: "#FF8C0010",
        text: "#FFA040",
        label: "bg-[#FF8C0020] text-[#FFA040] border-[#FF8C0040]",
    },
    medium: {
        border: "#FFB30040",
        bg: "#FFB30010",
        text: "#FFB300",
        label: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
    },
    low: {
        border: "#4CBB1740",
        bg: "#4CBB1710",
        text: "#4CBB17",
        label: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
    },
};

const SeverityIcon = ({ severity }) => {
    const cls = "h-4 w-4";
    if (severity === "critical") return <XCircle className={cls} />;
    if (severity === "high") return <AlertTriangle className={cls} />;
    if (severity === "medium") return <Clock className={cls} />;
    return <CheckCircle className={cls} />;
};

const QUICK_ACTIONS = [
    { label: "Detect Anomalies", prompt: "Check for anomalies in recent transactions", icon: AlertTriangle },
    { label: "Monitor KPIs", prompt: "Monitor all KPIs and create alerts if needed", icon: Bell },
    { label: "Check Overdue Items", prompt: "Check for overdue invoices and create alerts", icon: Clock },
    { label: "Prioritize Alerts", prompt: "Review and prioritize all notifications", icon: CheckCircle },
];

export default function AlertAgentPage() {
    const [alerts, setAlerts] = useState([]);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        initializeAgent();
        fetchAlerts();
    }, []);

    const initializeAgent = async () => {
        try {
            const data = {
                success: true,
                message: "Hello! I'm your Alert Agent. I'm monitoring your system for critical events.",
            };
            if (data.success) {
                setMessages([{
                    id: Date.now().toString(),
                    role: "assistant",
                    content: data.message,
                    timestamp: new Date(),
                }]);
            }
        } catch (error) {
            console.error("Failed to initialize alert agent:", error);
        }
    };

    const fetchAlerts = async () => {
        try {
            const mockAlerts = [
                {
                    id: "1",
                    type: "Anomaly",
                    severity: "high",
                    title: "Unusual Transaction Volume",
                    message: "Detected 40% spike in transaction volume in the last hour.",
                    actionRequired: true,
                    isRead: false,
                    createdAt: new Date().toISOString(),
                },
                {
                    id: "2",
                    type: "System",
                    severity: "low",
                    title: "Backup Completed",
                    message: "Daily system backup completed successfully.",
                    actionRequired: false,
                    isRead: true,
                    createdAt: new Date(Date.now() - 3600000).toISOString(),
                },
            ];
            setAlerts(mockAlerts);
        } catch (error) {
            console.error("Failed to fetch alerts:", error);
        }
    };

    const sendMessage = async (messageText) => {
        if (!messageText.trim()) return;
        const userMessage = {
            id: Date.now().toString(),
            role: "user",
            content: messageText,
            timestamp: new Date(),
        };
        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setIsLoading(true);
        try {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            setMessages((prev) => [...prev, {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: `I've analyzed your request: "${messageText}". All monitoring systems are currently operating normally.`,
                timestamp: new Date(),
            }]);
        } catch (error) {
            console.error("Error sending message:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const markAsRead = (alertId) =>
        setAlerts((prev) => prev.map((a) => a.id === alertId ? { ...a, isRead: true } : a));

    const dismissAlert = (alertId) =>
        setAlerts((prev) => prev.filter((a) => a.id !== alertId));

    const unreadCount = alerts.filter((a) => !a.isRead).length;

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="flex items-center gap-4">
                <div className="rounded-xl bg-[#FFB30020] border border-[#FFB30040] p-3">
                    <Bell className="h-6 w-6 text-[#FFB300]" />
                </div>
                <div>
                    <h1 className="mo-h1">Alert Agent</h1>
                    <p className="mo-text-secondary mt-0.5">
                        Monitor KPIs, detect anomalies, and manage priority notifications
                    </p>
                </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
                {/* ── Left: Alerts + Quick Actions ────────────────────────────── */}
                <div className="lg:col-span-2 flex flex-col gap-6">
                    {/* Active Alerts */}
                    <div className="mo-card">
                        <div className="flex items-center justify-between mb-4">
                            <div>
                                <h2 className="mo-h2">Active Alerts</h2>
                                <p className="mo-text-secondary mt-0.5">
                                    Current alerts and notifications requiring attention
                                </p>
                            </div>
                            {unreadCount > 0 && (
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-[#FFB30020] text-[#FFB300] border border-[#FFB30040]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-[#FFB300] animate-pulse" />
                                    {unreadCount} unread
                                </span>
                            )}
                        </div>
                        <div className="space-y-3">
                            {alerts.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-12 text-center">
                                    <Bell className="h-10 w-10 text-[#2A2A2A] mb-3" />
                                    <p className="text-[#A0A0A0] text-sm">No active alerts</p>
                                    <p className="text-xs text-[#A0A0A0] mt-1">Your Alert Agent is monitoring everything</p>
                                </div>
                            ) : (
                                alerts.map((alert) => {
                                    const sty = SEVERITY_STYLES[alert.severity] || SEVERITY_STYLES.low;
                                    return (
                                        <div
                                            key={alert.id}
                                            className="p-4 rounded-xl border transition-all"
                                            style={{
                                                backgroundColor: sty.bg,
                                                borderColor: alert.isRead ? "#2A2A2A" : sty.border,
                                            }}
                                        >
                                            <div className="flex items-start justify-between gap-4">
                                                <div className="flex items-start gap-3 flex-1 min-w-0">
                                                    <span style={{ color: sty.text }} className="mt-0.5 flex-shrink-0">
                                                        <SeverityIcon severity={alert.severity} />
                                                    </span>
                                                    <div className="flex-1 min-w-0">
                                                        <h4 className="font-semibold text-white text-sm">{alert.title}</h4>
                                                        <p className="text-sm text-[#A0A0A0] mt-0.5">{alert.message}</p>
                                                        <div className="flex items-center gap-2 mt-2 flex-wrap">
                                                            <span className="text-xs text-[#A0A0A0]">
                                                                {new Date(alert.createdAt).toLocaleString()}
                                                            </span>
                                                            <span className={`text-xs px-2 py-0.5 rounded-md font-medium border ${sty.label}`}>
                                                                {alert.severity}
                                                            </span>
                                                            <span className="text-xs px-2 py-0.5 rounded-md font-medium bg-[#A0A0A020] text-[#A0A0A0] border border-[#A0A0A040]">
                                                                {alert.type}
                                                            </span>
                                                            {alert.actionRequired && (
                                                                <span className="text-xs px-2 py-0.5 rounded-md font-medium bg-[#CD1C1820] text-[#CD1C18] border border-[#CD1C1840]">
                                                                    Action Required
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2 flex-shrink-0">
                                                    {!alert.isRead && (
                                                        <button
                                                            onClick={() => markAsRead(alert.id)}
                                                            className="text-xs px-3 py-1.5 rounded-lg text-[#A0A0A0] border border-[#2A2A2A] hover:border-[#4CBB17] hover:text-[#4CBB17] transition-all"
                                                        >
                                                            Mark Read
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => dismissAlert(alert.id)}
                                                        className="text-xs px-3 py-1.5 rounded-lg text-[#A0A0A0] hover:text-white hover:bg-[#2A2A2A] transition-all"
                                                    >
                                                        Dismiss
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    </div>

                    {/* Quick Actions */}
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-1">Quick Actions</h2>
                        <p className="mo-text-secondary mb-4">Common alert management tasks</p>
                        <div className="grid grid-cols-2 gap-3">
                            {QUICK_ACTIONS.map(({ label, prompt, icon: Icon }) => (
                                <button
                                    key={label}
                                    onClick={() => sendMessage(prompt)}
                                    disabled={isLoading}
                                    className="flex items-center gap-3 p-3 rounded-xl border border-[#2A2A2A] text-sm font-medium text-[#A0A0A0] hover:border-[#4CBB17] hover:text-white hover:bg-[#1A1A1A] transition-all text-left disabled:opacity-50"
                                >
                                    <Icon className="h-4 w-4 text-[#4CBB17] flex-shrink-0" />
                                    {label}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* ── Right: Chat ──────────────────────────────────────────────── */}
                <div className="mo-card !p-0 flex flex-col h-[600px]">
                    <div className="p-4 border-b border-[#2A2A2A]">
                        <div className="flex items-center gap-2">
                            <Bell className="h-4 w-4 text-[#4CBB17]" />
                            <h3 className="text-sm font-semibold text-white">Alert Agent Chat</h3>
                            <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-[#4CBB1720] text-[#4CBB17] border border-[#4CBB1740]">
                                Active
                            </span>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-3">
                        {messages.map((message) => (
                            <div
                                key={message.id}
                                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                            >
                                <div
                                    className={`max-w-[85%] rounded-xl p-3 text-sm ${message.role === "user"
                                            ? "bg-[#4CBB17] text-black"
                                            : "bg-[#1A1A1A] border border-[#2A2A2A] text-[#A0A0A0]"
                                        }`}
                                >
                                    <div className="text-[10px] mb-1.5 opacity-60">
                                        {message.role === "user" ? "You" : "Alert Agent"} ·{" "}
                                        {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                                    </div>
                                    <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
                                </div>
                            </div>
                        ))}
                        {isLoading && (
                            <div className="flex justify-start">
                                <div className="bg-[#1A1A1A] border border-[#2A2A2A] rounded-xl p-3 text-sm text-[#A0A0A0]">
                                    <div className="flex items-center gap-2 mb-1.5">
                                        <Bell className="h-3.5 w-3.5 text-[#4CBB17]" />
                                        <span className="text-xs text-[#A0A0A0]">Analyzing alerts…</span>
                                    </div>
                                    <div className="flex gap-1">
                                        {[0, 0.15, 0.3].map((delay, i) => (
                                            <div
                                                key={i}
                                                className="w-1.5 h-1.5 bg-[#4CBB17] rounded-full animate-bounce"
                                                style={{ animationDelay: `${delay}s` }}
                                            />
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Input */}
                    <form
                        onSubmit={(e) => { e.preventDefault(); sendMessage(input); }}
                        className="p-4 border-t border-[#2A2A2A] flex gap-2"
                    >
                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="Ask about alerts, KPIs, or anomalies…"
                            disabled={isLoading}
                            className="flex-1 px-3 py-2 rounded-lg text-sm text-white placeholder-[#A0A0A0] focus:outline-none focus:border-[#4CBB17]"
                            style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                        />
                        <button
                            type="submit"
                            disabled={isLoading || !input.trim()}
                            className="p-2 rounded-lg bg-[#4CBB17] text-black hover:opacity-90 transition-opacity disabled:opacity-40"
                        >
                            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
