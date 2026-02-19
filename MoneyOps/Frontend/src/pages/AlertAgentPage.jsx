import { useState, useEffect } from "react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
    Bell,
    AlertTriangle,
    CheckCircle,
    XCircle,
    Clock,
    Send,
} from "lucide-react";

export default function AlertAgentPage() {
    const [alerts, setAlerts] = useState([]);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [sessionId] = useState(`alert-session-${Date.now()}`);

    useEffect(() => {
        initializeAgent();
        fetchAlerts();
    }, []);

    const initializeAgent = async () => {
        try {
            // Simulate init for demo
            const data = {
                success: true,
                message: "Hello! I'm your Alert Agent. I'm monitoring your system for critical events.",
            };

            if (data.success) {
                setMessages([
                    {
                        id: Date.now().toString(),
                        role: "assistant",
                        content: data.message,
                        timestamp: new Date(),
                    },
                ]);
            }
        } catch (error) {
            console.error("Failed to initialize alert agent:", error);
        }
    };

    const fetchAlerts = async () => {
        try {
            // Simulated alerts for demo
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
            // Simulate agent response
            await new Promise((resolve) => setTimeout(resolve, 1000));

            const assistantMessage = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: `I've received your request: "${messageText}". Monitoring systems are normal.`,
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            console.error("Error sending message:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        sendMessage(input);
    };

    const getSeverityColor = (severity) => {
        switch (severity) {
            case "critical":
                return "bg-red-100 text-red-800 border-red-200";
            case "high":
                return "bg-orange-100 text-orange-800 border-orange-200";
            case "medium":
                return "bg-yellow-100 text-yellow-800 border-yellow-200";
            case "low":
                return "bg-blue-100 text-blue-800 border-blue-200";
            default:
                return "bg-slate-100 text-slate-800 border-slate-200";
        }
    };

    const getSeverityIcon = (severity) => {
        switch (severity) {
            case "critical":
                return <XCircle className="h-4 w-4" />;
            case "high":
                return <AlertTriangle className="h-4 w-4" />;
            case "medium":
                return <Clock className="h-4 w-4" />;
            case "low":
                return <CheckCircle className="h-4 w-4" />;
            default:
                return <Bell className="h-4 w-4" />;
        }
    };

    const markAsRead = async (alertId) => {
        setAlerts((prev) =>
            prev.map((alert) =>
                alert.id === alertId ? { ...alert, isRead: true } : alert
            )
        );
    };

    const dismissAlert = async (alertId) => {
        setAlerts((prev) => prev.filter((alert) => alert.id !== alertId));
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center space-x-3">
                <div className="p-2 bg-orange-100 rounded-lg">
                    <Bell className="h-6 w-6 text-orange-600" />
                </div>
                <div>
                    <h1 className="text-2xl font-bold">Alert Agent</h1>
                    <p className="text-muted-foreground">
                        Monitor KPIs, detect anomalies, and manage priority notifications
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Active Alerts */}
                <div className="lg:col-span-2 space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center justify-between">
                                <span>Active Alerts</span>
                                <Badge variant="secondary">
                                    {alerts.filter((a) => !a.isRead).length} unread
                                </Badge>
                            </CardTitle>
                            <CardDescription>
                                Current alerts and notifications requiring attention
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-3">
                                {alerts.length === 0 ? (
                                    <div className="text-center py-8 text-muted-foreground">
                                        <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                        <p>No active alerts</p>
                                        <p className="text-sm">
                                            Your Alert Agent is monitoring everything
                                        </p>
                                    </div>
                                ) : (
                                    alerts.map((alert) => (
                                        <div
                                            key={alert.id}
                                            className={`p-4 rounded-lg border ${getSeverityColor(
                                                alert.severity
                                            )} ${!alert.isRead ? "ring-2 ring-offset-2 ring-current" : ""
                                                }`}
                                        >
                                            <div className="flex items-start justify-between">
                                                <div className="flex items-start space-x-3">
                                                    {getSeverityIcon(alert.severity)}
                                                    <div className="flex-1">
                                                        <h4 className="font-medium">{alert.title}</h4>
                                                        <p className="text-sm mt-1">{alert.message}</p>
                                                        <div className="flex items-center space-x-4 mt-2 text-xs">
                                                            <span>
                                                                {new Date(alert.createdAt).toLocaleString()}
                                                            </span>
                                                            <Badge variant="outline" className="text-xs">
                                                                {alert.type}
                                                            </Badge>
                                                            {alert.actionRequired && (
                                                                <Badge
                                                                    variant="destructive"
                                                                    className="text-xs"
                                                                >
                                                                    Action Required
                                                                </Badge>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex space-x-2">
                                                    {!alert.isRead && (
                                                        <Button
                                                            size="sm"
                                                            variant="outline"
                                                            onClick={() => markAsRead(alert.id)}
                                                        >
                                                            Mark Read
                                                        </Button>
                                                    )}
                                                    <Button
                                                        size="sm"
                                                        variant="ghost"
                                                        onClick={() => dismissAlert(alert.id)}
                                                    >
                                                        Dismiss
                                                    </Button>
                                                </div>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Quick Actions */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Quick Actions</CardTitle>
                            <CardDescription>Common alert management tasks</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-2 gap-3">
                                <Button
                                    variant="outline"
                                    onClick={() =>
                                        sendMessage("Check for anomalies in recent transactions")
                                    }
                                    disabled={isLoading}
                                >
                                    <AlertTriangle className="h-4 w-4 mr-2" />
                                    Detect Anomalies
                                </Button>
                                <Button
                                    variant="outline"
                                    onClick={() =>
                                        sendMessage("Monitor all KPIs and create alerts if needed")
                                    }
                                    disabled={isLoading}
                                >
                                    <Bell className="h-4 w-4 mr-2" />
                                    Monitor KPIs
                                </Button>
                                <Button
                                    variant="outline"
                                    onClick={() =>
                                        sendMessage("Check for overdue invoices and create alerts")
                                    }
                                    disabled={isLoading}
                                >
                                    <Clock className="h-4 w-4 mr-2" />
                                    Check Overdue Items
                                </Button>
                                <Button
                                    variant="outline"
                                    onClick={() =>
                                        sendMessage("Review and prioritize all notifications")
                                    }
                                    disabled={isLoading}
                                >
                                    <CheckCircle className="h-4 w-4 mr-2" />
                                    Prioritize Alerts
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Chat Interface */}
                <div className="space-y-4">
                    <Card className="h-[600px] flex flex-col">
                        <CardHeader>
                            <CardTitle className="flex items-center space-x-2">
                                <Bell className="h-5 w-5" />
                                <span>Alert Agent Chat</span>
                                <Badge variant="default">Active</Badge>
                            </CardTitle>
                        </CardHeader>

                        <CardContent className="flex-1 flex flex-col">
                            <div className="flex-1 overflow-y-auto space-y-4 mb-4">
                                {messages.map((message) => (
                                    <div
                                        key={message.id}
                                        className={`flex ${message.role === "user"
                                                ? "justify-end"
                                                : "justify-start"
                                            }`}
                                    >
                                        <div
                                            className={`max-w-[80%] rounded-lg p-3 ${message.role === "user"
                                                    ? "bg-primary text-primary-foreground"
                                                    : "bg-slate-100"
                                                }`}
                                        >
                                            <div className="flex items-center space-x-2 mb-1">
                                                {message.role === "user" ? (
                                                    <span className="text-xs opacity-70">You</span>
                                                ) : (
                                                    <span className="text-xs opacity-70">
                                                        Alert Agent
                                                    </span>
                                                )}
                                                <span className="text-xs opacity-50">
                                                    {message.timestamp.toLocaleTimeString()}
                                                </span>
                                            </div>
                                            <p className="text-sm whitespace-pre-wrap">
                                                {message.content}
                                            </p>
                                        </div>
                                    </div>
                                ))}

                                {isLoading && (
                                    <div className="flex justify-start">
                                        <div className="bg-slate-100 rounded-lg p-3">
                                            <div className="flex items-center space-x-2">
                                                <Bell className="h-4 w-4" />
                                                <span className="text-xs">Analyzing alerts...</span>
                                            </div>
                                            <div className="flex space-x-1 mt-2">
                                                <div className="w-2 h-2 bg-current rounded-full animate-bounce"></div>
                                                <div
                                                    className="w-2 h-2 bg-current rounded-full animate-bounce"
                                                    style={{ animationDelay: "0.1s" }}
                                                ></div>
                                                <div
                                                    className="w-2 h-2 bg-current rounded-full animate-bounce"
                                                    style={{ animationDelay: "0.2s" }}
                                                ></div>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <form onSubmit={handleSubmit} className="flex space-x-2">
                                <Input
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    placeholder="Ask me about alerts, KPIs, or anomalies..."
                                    disabled={isLoading}
                                    className="flex-1"
                                />
                                <Button type="submit" disabled={isLoading || !input.trim()}>
                                    <Send className="h-4 w-4" />
                                </Button>
                            </form>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
