import { useState, useEffect } from "react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Shield,
    AlertTriangle,
    CheckCircle2,
    FileText,
    RefreshCw,
    Download,
    Calendar as CalendarIcon,
    AlertCircle,
    Calculator,
} from "lucide-react";
import { AgentInsights } from "./dashboard/agent-insights";
import { toast } from "sonner";

export function ComplianceDashboard({ businessId, data, onRefresh }) {
    const [activeTab, setActiveTab] = useState("overview");
    const [date, setDate] = useState(new Date());
    const [deadlines, setDeadlines] = useState([]);
    const [calcResult, setCalcResult] = useState(null);
    const [formData, setFormData] = useState({
        amount: "",
        category: "professional",
        isIndividual: "true",
    });

    // Load deadlines
    useEffect(() => {
        fetch(`/api/deadlines?businessId=${businessId}`)
            .then((res) => {
                if (!res.ok) throw new Error("Failed to fetch");
                return res.json();
            })
            .then((data) => setDeadlines(data.deadlines || []))
            .catch((err) => {
                console.error(err);
                // Mock deadlines fallback
                setDeadlines([
                    {
                        id: 1,
                        title: "GST Filing (Dec)",
                        dueDate: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 20).toISOString().split('T')[0],
                        type: "GST",
                        priority: "high",
                    },
                    {
                        id: 2,
                        title: "TDS Payment",
                        dueDate: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 7).toISOString().split('T')[0],
                        type: "TDS",
                        priority: "high",
                    },
                ]);
            });
    }, [businessId]);

    // Mock data if not provided
    const complianceScore = data?.score || 85;
    const pendingTasks = data?.pendingTasks || [
        {
            id: 1,
            title: "GST Filing for December",
            dueDate: "2025-01-20",
            priority: "high",
            status: "pending",
            type: "GST",
        },
        {
            id: 2,
            title: "FY 2024-25 Annual Return",
            dueDate: "2025-07-31",
            priority: "medium",
            status: "pending",
            type: "ITR",
        },
        {
            id: 3,
            title: "Q3 TDS Return Filing",
            dueDate: "2025-01-31",
            priority: "high",
            status: "pending",
            type: "TDS",
        },
    ];

    const recentAlerts = data?.alerts || [
        {
            id: 1,
            title: "New GST Regulation Update",
            date: "2025-01-05",
            type: "info",
        },
        {
            id: 2,
            title: "Potential Input Tax Credit Mismatch",
            date: "2024-12-15",
            type: "warning",
        },
    ];

    async function onCalculate() {
        try {
            const res = await fetch("/api/tds/calc", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    amount: parseFloat(formData.amount),
                    category: formData.category,
                    isIndividual: formData.isIndividual === "true",
                }),
            });

            if (!res.ok) throw new Error("Calculation failed");

            const result = await res.json();
            setCalcResult(result);
            toast.success("TDS calculated successfully");
        } catch (e) {
            console.error(e);
            toast.error("Calculation failed - using fallback calculation");

            // Fallback calculation
            const amount = parseFloat(formData.amount) || 0;
            let rate = 10; // Default rate
            let section = "194J";

            switch (formData.category) {
                case "professional":
                    rate = formData.isIndividual === "true" ? 10 : 10;
                    section = "194J";
                    break;
                case "contract":
                    rate = formData.isIndividual === "true" ? 1 : 2;
                    section = "194C";
                    break;
                case "rent":
                    rate = 10;
                    section = "194I";
                    break;
                case "commission":
                    rate = 5;
                    section = "194H";
                    break;
            }

            setCalcResult({
                section,
                rate,
                deductible: ((amount * rate) / 100).toFixed(2),
            });
        }
    }

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">
                        Compliance & Tax Agent
                    </h2>
                    <p className="text-muted-foreground">
                        Monitor regulatory compliance and tax obligations
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={onRefresh}>
                        <RefreshCw className="mr-2 h-4 w-4" />
                        Refresh
                    </Button>
                    <Button size="sm">
                        <Download className="mr-2 h-4 w-4" />
                        Export Report
                    </Button>
                </div>
            </div>

            {/* Compliance Score & Quick Stats */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">
                            Compliance Score
                        </CardTitle>
                        <Shield
                            className={`h-4 w-4 ${complianceScore >= 80 ? "text-green-500" : "text-yellow-500"
                                }`}
                        />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{complianceScore}/100</div>
                        <p className="text-xs text-muted-foreground">
                            {complianceScore >= 80 ? "Good standing" : "Attention needed"}
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Pending Filings</CardTitle>
                        <FileText className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{pendingTasks.length}</div>
                        <p className="text-xs text-muted-foreground">Due within 30 days</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Risk Alerts</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{recentAlerts.length}</div>
                        <p className="text-xs text-muted-foreground">
                            Requires immediate attention
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Next Deadline</CardTitle>
                        <CalendarIcon className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">Jan 20</div>
                        <p className="text-xs text-muted-foreground">GST Filing</p>
                    </CardContent>
                </Card>
            </div>

            {/* Main Tabs */}
            <Tabs defaultValue="overview" className="space-y-4">
                <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="calendar">Calendar</TabsTrigger>
                    <TabsTrigger value="tds">TDS Calculator</TabsTrigger>
                    <TabsTrigger value="documents">Documents</TabsTrigger>
                </TabsList>

                {/* Overview Tab */}
                <TabsContent value="overview">
                    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
                        <Card className="col-span-4">
                            <CardHeader>
                                <CardTitle>Compliance Tasks</CardTitle>
                                <CardDescription>
                                    Manage your tax filings and regulatory tasks
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ScrollArea className="h-[400px]">
                                    <div className="space-y-3">
                                        {pendingTasks.map((task) => (
                                            <div
                                                key={task.id}
                                                className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50"
                                            >
                                                <div className="flex items-center gap-4">
                                                    <div
                                                        className={`p-2 rounded-full ${task.priority === "high"
                                                                ? "bg-red-100 text-red-600"
                                                                : task.priority === "medium"
                                                                    ? "bg-yellow-100 text-yellow-600"
                                                                    : "bg-blue-100 text-blue-600"
                                                            }`}
                                                    >
                                                        <AlertCircle className="h-4 w-4" />
                                                    </div>
                                                    <div>
                                                        <div className="flex items-center gap-2">
                                                            <h4 className="font-semibold">{task.title}</h4>
                                                            <Badge variant="outline">{task.type}</Badge>
                                                        </div>
                                                        <p className="text-sm text-muted-foreground">
                                                            Due: {task.dueDate}
                                                        </p>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <Badge
                                                        variant={
                                                            task.status === "overdue"
                                                                ? "destructive"
                                                                : "secondary"
                                                        }
                                                    >
                                                        {task.status}
                                                    </Badge>
                                                    <Button size="sm" variant="ghost">
                                                        View
                                                    </Button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </ScrollArea>
                            </CardContent>
                        </Card>

                        <div className="col-span-3 space-y-6">
                            <AgentInsights
                                agentName="Compliance Agent"
                                insights={[
                                    {
                                        id: "1",
                                        agentType: "compliance",
                                        taskDescription: "check_compliance",
                                        output: {
                                            message:
                                                "Your GST filing frequency is set to Monthly. Next deadline is April 20th.",
                                        },
                                        completedAt: new Date().toISOString(),
                                        duration: 120,
                                    },
                                    {
                                        id: "2",
                                        agentType: "compliance",
                                        taskDescription: "check_compliance",
                                        output: {
                                            message:
                                                "Detected a potential mismatch in Input Tax Credit for March invoice #INV-003.",
                                        },
                                        completedAt: new Date().toISOString(),
                                        duration: 150,
                                    },
                                    {
                                        id: "3",
                                        agentType: "compliance",
                                        taskDescription: "check_compliance",
                                        output: {
                                            message:
                                                "New regulation update: E-invoicing threshold lowered to ₹5 Cr effective from next fiscal year.",
                                        },
                                        completedAt: new Date().toISOString(),
                                        duration: 100,
                                    },
                                ]}
                            />

                            <Card>
                                <CardHeader>
                                    <CardTitle>Recent Alerts</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <ScrollArea className="h-[200px]">
                                        <div className="space-y-3">
                                            {recentAlerts.map((alert) => (
                                                <div
                                                    key={alert.id}
                                                    className="flex gap-3 items-start p-2 rounded hover:bg-muted/50"
                                                >
                                                    <div
                                                        className={`mt-0.5 h-2 w-2 rounded-full ${alert.type === "warning"
                                                                ? "bg-yellow-500"
                                                                : "bg-blue-500"
                                                            }`}
                                                    />
                                                    <div>
                                                        <p className="text-sm font-medium leading-none">
                                                            {alert.title}
                                                        </p>
                                                        <p className="text-xs text-muted-foreground mt-1">
                                                            {alert.date}
                                                        </p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </ScrollArea>
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </TabsContent>

                {/* Calendar Tab */}
                <TabsContent value="calendar">
                    <div className="grid gap-6 md:grid-cols-2">
                        <Card>
                            <CardHeader>
                                <CardTitle>Upcoming Deadlines</CardTitle>
                                <CardDescription>
                                    Mark important compliance dates
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <ScrollArea className="h-[400px]">
                                    {deadlines.length === 0 && pendingTasks.length > 0 ? (
                                        <div className="space-y-3">
                                            {pendingTasks.map((dl) => (
                                                <div
                                                    key={dl.id}
                                                    className="flex items-center justify-between p-4 border rounded-lg"
                                                >
                                                    <div>
                                                        <h4 className="font-semibold">{dl.title}</h4>
                                                        <p className="text-sm text-muted-foreground">
                                                            Due: {dl.dueDate}
                                                        </p>
                                                    </div>
                                                    <Badge
                                                        variant={
                                                            dl.priority === "high" ? "destructive" : "default"
                                                        }
                                                    >
                                                        {dl.type}
                                                    </Badge>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-center py-8 text-muted-foreground">
                                            No pending deadlines.
                                        </div>
                                    )}
                                </ScrollArea>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>Calendar</CardTitle>
                                <CardDescription>View deadlines by date</CardDescription>
                            </CardHeader>
                            <CardContent className="flex justify-center">
                                <Calendar
                                    mode="single"
                                    selected={date}
                                    onSelect={setDate}
                                    className="rounded-md border"
                                />
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* TDS Calculator Tab */}
                <TabsContent value="tds">
                    <div className="grid gap-6 md:grid-cols-2">
                        <Card>
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2">
                                    <Calculator className="h-5 w-5" />
                                    TDS Calculator
                                </CardTitle>
                                <CardDescription>
                                    Calculate TDS deductions for various payment categories
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    <Label>Payment Amount (₹)</Label>
                                    <Input
                                        type="number"
                                        value={formData.amount}
                                        onChange={(e) =>
                                            setFormData({ ...formData, amount: e.target.value })
                                        }
                                        placeholder="Enter payment amount"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label>Category</Label>
                                    <Select
                                        value={formData.category}
                                        onValueChange={(v) =>
                                            setFormData({ ...formData, category: v })
                                        }
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="professional">
                                                Professional Fees (194J)
                                            </SelectItem>
                                            <SelectItem value="contract">Contractor (194C)</SelectItem>
                                            <SelectItem value="rent">Rent (194I)</SelectItem>
                                            <SelectItem value="commission">
                                                Commission (194H)
                                            </SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label>Payee Type</Label>
                                    <Select
                                        value={formData.isIndividual}
                                        onValueChange={(v) =>
                                            setFormData({ ...formData, isIndividual: v })
                                        }
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="true">Individual/HUF</SelectItem>
                                            <SelectItem value="false">Company/Firm</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <Button
                                    onClick={onCalculate}
                                    className="w-full"
                                    disabled={!formData.amount}
                                >
                                    <Calculator className="mr-2 h-4 w-4" />
                                    Calculate TDS
                                </Button>

                                {calcResult && (
                                    <div className="mt-4 p-4 bg-primary/10 rounded-lg border border-primary/20">
                                        <h4 className="font-semibold mb-3">Calculation Result</h4>
                                        <div className="space-y-2 text-sm">
                                            <div className="flex justify-between">
                                                <span className="text-muted-foreground">Section:</span>
                                                <span className="font-semibold">
                                                    {calcResult.section}
                                                </span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-muted-foreground">Rate:</span>
                                                <span className="font-semibold">{calcResult.rate}%</span>
                                            </div>
                                            <div className="flex justify-between border-t pt-2">
                                                <span className="text-muted-foreground">
                                                    TDS to Deduct:
                                                </span>
                                                <span className="font-bold text-lg text-primary">
                                                    ₹{calcResult.deductible}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>Outstanding TDS Liabilities</CardTitle>
                                <CardDescription>
                                    Track pending TDS payments and returns
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                <div className="text-center text-muted-foreground py-12">
                                    <CheckCircle2 className="h-12 w-12 mx-auto mb-3 opacity-20" />
                                    <p>No outstanding liabilities found.</p>
                                    <p className="text-sm mt-1">All TDS payments are up to date</p>
                                </div>
                            </CardContent>
                        </Card>
                    </div>
                </TabsContent>

                {/* Documents Tab */}
                <TabsContent value="documents">
                    <Card>
                        <CardHeader>
                            <CardTitle>Compliance Documents</CardTitle>
                            <CardDescription>
                                Upload and manage compliance-related documents
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="h-[400px] flex items-center justify-center text-muted-foreground border-2 border-dashed rounded-lg">
                                <div className="text-center">
                                    <FileText className="h-16 w-16 mx-auto mb-3 opacity-20" />
                                    <p>No compliance documents found</p>
                                    <p className="text-sm mt-1">Upload documents to get started</p>
                                    <Button variant="outline" className="mt-4">
                                        <Download className="mr-2 h-4 w-4" />
                                        Upload Document
                                    </Button>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
