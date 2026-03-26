import { useEffect, useState } from "react";
import {
    Shield, AlertTriangle, CheckCircle2, FileText, RefreshCw,
    Download, Calendar as CalendarIcon, AlertCircle, Calculator,
} from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { useAuth } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";

const PRIORITY_BADGE = {
    high: "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]",
    medium: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
    low: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
};

const PRIORITY_DOT = { high: "#CD1C18", medium: "#FFB300", low: "#4CBB17" };

const inputStyle = {
    backgroundColor: "#1A1A1A",
    border: "1px solid #2A2A2A",
    borderRadius: "8px",
    color: "#ffffff",
    padding: "8px 12px",
    fontSize: "14px",
    width: "100%",
    outline: "none",
};

function DarkInput({ ...props }) {
    return (
        <input
            {...props}
            style={{ ...inputStyle, ...(props.style || {}) }}
            onFocus={(e) => { e.target.style.borderColor = "#4CBB17"; }}
            onBlur={(e) => { e.target.style.borderColor = "#2A2A2A"; }}
        />
    );
}

function StatCard({ label, value, sub, icon: Icon, iconColor, accent }) {
    return (
        <div className="mo-card">
            <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-[#A0A0A0] font-medium uppercase tracking-wide">{label}</p>
                {Icon && <Icon className="h-4 w-4" style={{ color: iconColor || "#A0A0A0" }} />}
            </div>
            <p className="text-2xl font-bold" style={{ color: accent || "#ffffff" }}>{value}</p>
            {sub && <p className="text-xs text-[#A0A0A0] mt-1">{sub}</p>}
        </div>
    );
}

export function ComplianceDashboard({ businessId, data, onRefresh }) {
    const { getToken } = useAuth();
    const { userId: internalUserId, orgId: internalOrgId } = useOnboardingStatus();
    const [activeTab, setActiveTab] = useState("overview");
    const [date, setDate] = useState(new Date());
    const [deadlines, setDeadlines] = useState([]);
    const [calcResult, setCalcResult] = useState(null);
    const [formData, setFormData] = useState({ amount: "", category: "professional", isIndividual: "true" });

    useEffect(() => {
        const fetchDeadlines = async () => {
            if (!businessId || !internalUserId || !internalOrgId) return;
            try {
                const token = await getToken();
                const res = await fetch(`/api/deadlines?businessId=${businessId}`, {
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "X-User-Id": internalUserId,
                        "X-Org-Id": internalOrgId,
                    },
                });
                if (!res.ok) throw new Error("Failed to fetch deadlines");
                const json = await res.json();
                setDeadlines(json.deadlines || []);
            } catch (error) {
                console.error(error);
                setDeadlines([]);
            }
        };

        fetchDeadlines();
    }, [businessId, internalUserId, internalOrgId, getToken]);

    const complianceScore = data?.complianceScore ?? data?.compliance_score ?? data?.score ?? 85;
    const rawUpcomingDeadlines = data?.upcomingDeadlines || data?.upcoming_deadlines || [];
    const pendingTasks = rawUpcomingDeadlines.map((deadline, index) => ({
        id: deadline.id || index,
        title: deadline.filing || deadline.title || "Filing",
        dueDate: deadline.due_date || deadline.dueDate,
        priority: deadline.priority || (deadline.status === "urgent" ? "high" : "medium"),
        status: deadline.status || "pending",
        type: deadline.type || (deadline.filing?.includes("GST") ? "GST" : "TAX"),
    }));

    const fallbackPendingTasks = [
        { id: 1, title: "GST Filing", dueDate: "2025-01-20", priority: "high", status: "pending", type: "GST" },
        { id: 2, title: "Annual Return", dueDate: "2025-07-31", priority: "medium", status: "pending", type: "ITR" },
    ];
    const effectivePendingTasks = pendingTasks.length ? pendingTasks : fallbackPendingTasks;

    const currentDate = new Date().toISOString().split("T")[0];
    const recentAlerts = (data?.alerts || []).map((alert, index) => ({
        id: index,
        title: alert.replace(/^[^A-Za-z0-9]+/, ""),
        date: currentDate,
        type: alert.toLowerCase().includes("no immediate") ? "info" : "warning",
    }));
    const effectiveRecentAlerts = recentAlerts.length
        ? recentAlerts
        : [{ id: 1, title: "No immediate compliance risks detected", date: currentDate, type: "info" }];

    const agentSummary = data?.keyRequirements || data?.key_requirements || [
        "Review GST and TDS filing deadlines.",
        "Track invoice and payment reconciliation.",
        "Maintain supporting documentation for audits.",
    ];

    async function onCalculate() {
        try {
            const token = await getToken();
            const res = await fetch("/api/tds/calc", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId,
                },
                body: JSON.stringify({
                    amount: parseFloat(formData.amount),
                    category: formData.category,
                    isIndividual: formData.isIndividual === "true",
                }),
            });
            if (!res.ok) throw new Error("Calculation failed");
            setCalcResult(await res.json());
            toast.success("TDS calculated successfully");
        } catch (error) {
            console.error(error);
            toast.error("Failed to calculate TDS");
        }
    }

    function exportJson(filename, payload) {
        const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }

    const auditData = data?.auditReadiness || data?.audit_readiness || {};
    const healthColor = complianceScore >= 80 ? "#4CBB17" : complianceScore >= 60 ? "#FFB300" : "#CD1C18";
    const tabs = [
        { id: "overview", label: "Overview" },
        { id: "calendar", label: "Calendar" },
        { id: "tds", label: "TDS Calculator" },
        { id: "documents", label: "Audit & Docs" },
    ];

    const nextDeadline = data?.nextDeadline || effectivePendingTasks[0] || null;
    const nextDeadlineValue = nextDeadline?.dueDate
        ? `${nextDeadline.dueDate.split("-")[2]} ${new Date(nextDeadline.dueDate).toLocaleString("default", { month: "short" })}`
        : "No Due";

    return (
        <div className="flex flex-col gap-6">
            <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-4">
                    <div className="rounded-xl p-3" style={{ backgroundColor: "#60A5FA20", border: "1px solid #60A5FA40" }}>
                        <Shield className="h-6 w-6 text-[#60A5FA]" />
                    </div>
                    <div>
                        <h1 className="mo-h1">Compliance & Tax Agent</h1>
                        <p className="mo-text-secondary mt-0.5">Monitor regulatory compliance and tax obligations</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={onRefresh} className="mo-btn-secondary flex items-center gap-2 text-sm">
                        <RefreshCw className="h-4 w-4" /> Refresh
                    </button>
                    <button
                        onClick={() => exportJson(`compliance-report-${new Date().toISOString().slice(0, 10)}.json`, {
                            generatedAt: new Date().toISOString(),
                            complianceData: data,
                            deadlines,
                        })}
                        className="mo-btn-primary flex items-center gap-2 text-sm"
                    >
                        <Download className="h-4 w-4" /> Export Report
                    </button>
                </div>
            </div>

            <div className="grid gap-4 md:grid-cols-4">
                <div className="mo-card" style={{ borderColor: `${healthColor}30` }}>
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-xs text-[#A0A0A0] font-medium uppercase tracking-wide">Compliance Score</p>
                        <Shield className="h-4 w-4" style={{ color: healthColor }} />
                    </div>
                    <p className="text-2xl font-bold" style={{ color: healthColor }}>{complianceScore}/100</p>
                    <p className="text-xs text-[#A0A0A0] mt-1">{complianceScore >= 80 ? "Good standing" : "Attention needed"}</p>
                </div>
                <StatCard label="Pending Filings" value={data?.pendingFilings ?? effectivePendingTasks.length} sub="Due within 30 days" icon={FileText} iconColor="#A0A0A0" />
                <StatCard label="Risk Alerts" value={data?.riskAlerts ?? effectiveRecentAlerts.length} sub="Requires attention" icon={AlertTriangle} iconColor="#CD1C18" accent="#CD1C18" />
                <StatCard label="Next Deadline" value={nextDeadlineValue} sub={nextDeadline?.title || nextDeadline?.filing || "All clear"} icon={CalendarIcon} iconColor="#A0A0A0" />
            </div>

            <div className="mo-card !p-0">
                <div className="flex border-b border-[#2A2A2A] px-4 overflow-x-auto">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`px-4 py-3.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === tab.id ? "border-[#4CBB17] text-[#4CBB17]" : "border-transparent text-[#A0A0A0] hover:text-white"}`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                <div className="p-5">
                    {activeTab === "overview" && (
                        <div className="grid gap-6 lg:grid-cols-7">
                            <div className="lg:col-span-4 flex flex-col gap-3">
                                <h3 className="font-semibold text-white mb-1">Compliance Tasks</h3>
                                {effectivePendingTasks.map((task) => (
                                    <div key={task.id} className="flex items-center justify-between p-4 rounded-xl border border-[#2A2A2A] hover:border-[#3A3A3A] transition-all">
                                        <div className="flex items-center gap-3">
                                            <div className="p-2 rounded-full" style={{ backgroundColor: (PRIORITY_DOT[task.priority] || PRIORITY_DOT.low) + "20", color: PRIORITY_DOT[task.priority] || PRIORITY_DOT.low }}>
                                                <AlertCircle className="h-4 w-4" />
                                            </div>
                                            <div>
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <h4 className="font-semibold text-white text-sm">{task.title}</h4>
                                                    <span className={`text-xs px-2 py-0.5 rounded-md font-medium border ${PRIORITY_BADGE[task.priority] || PRIORITY_BADGE.low}`}>{task.type}</span>
                                                </div>
                                                <p className="text-xs text-[#A0A0A0] mt-0.5">Due: {task.dueDate}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className={`text-xs px-2 py-0.5 rounded-md border ${task.status === "overdue" ? "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]" : "bg-[#A0A0A020] text-[#A0A0A0] border-[#A0A0A040]"}`}>{task.status}</span>
                                            <button
                                                onClick={() => {
                                                    setActiveTab("calendar");
                                                    if (task.dueDate) setDate(new Date(task.dueDate));
                                                }}
                                                className="text-xs text-[#A0A0A0] hover:text-[#4CBB17] transition-colors px-2"
                                            >
                                                View
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="lg:col-span-3 flex flex-col gap-4">
                                <div className="rounded-xl border border-[#2A2A2A] p-4">
                                    <h3 className="font-semibold text-white mb-3 text-sm">Agent Summary</h3>
                                    <div className="flex flex-col gap-3">
                                        {agentSummary.map((msg, index) => (
                                            <div key={index} className="flex gap-2 text-sm">
                                                <div className="w-1.5 h-1.5 mt-1.5 rounded-full bg-[#4CBB17] flex-shrink-0" />
                                                <p className="text-[#A0A0A0]">{msg}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="rounded-xl border border-[#2A2A2A] p-4">
                                    <h3 className="font-semibold text-white mb-3 text-sm">Recent Alerts</h3>
                                    <div className="flex flex-col gap-3">
                                        {effectiveRecentAlerts.map((alert) => (
                                            <div key={alert.id} className="flex gap-3 items-start">
                                                <div className="mt-1.5 h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: alert.type === "warning" ? "#FFB300" : "#60A5FA" }} />
                                                <div>
                                                    <p className="text-sm font-medium text-white">{alert.title}</p>
                                                    <p className="text-xs text-[#A0A0A0] mt-0.5">{alert.date}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === "calendar" && (
                        <div className="grid gap-6 md:grid-cols-2">
                            <div>
                                <h3 className="font-semibold text-white mb-3">Upcoming Deadlines</h3>
                                <div className="flex flex-col gap-3">
                                    {(deadlines.length > 0 ? deadlines : effectivePendingTasks).map((deadline) => (
                                        <div key={deadline.id} className="flex items-center justify-between p-4 rounded-xl border border-[#2A2A2A] hover:border-[#3A3A3A] transition-all">
                                            <div>
                                                <h4 className="font-semibold text-white text-sm">{deadline.title}</h4>
                                                <p className="text-xs text-[#A0A0A0] mt-0.5">Due: {deadline.dueDate}</p>
                                            </div>
                                            <span className={`text-xs px-2 py-0.5 rounded-md font-medium border ${PRIORITY_BADGE[deadline.priority] || PRIORITY_BADGE.medium}`}>{deadline.type}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <h3 className="font-semibold text-white mb-3">Calendar</h3>
                                <div className="rounded-xl border border-[#2A2A2A] overflow-hidden flex justify-center p-2" style={{ backgroundColor: "#1A1A1A" }}>
                                    <Calendar mode="single" selected={date} onSelect={setDate} className="rounded-md" />
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === "tds" && (
                        <div className="grid gap-6 md:grid-cols-2">
                            <div className="flex flex-col gap-4">
                                <div className="flex items-center gap-2 mb-1">
                                    <Calculator className="h-5 w-5 text-[#4CBB17]" />
                                    <h3 className="font-semibold text-white">TDS Calculator</h3>
                                </div>
                                <p className="text-sm text-[#A0A0A0] -mt-2">Calculate TDS deductions for various payment categories</p>

                                <div>
                                    <label className="text-xs text-[#A0A0A0] block mb-1.5">Payment Amount (INR)</label>
                                    <DarkInput type="number" value={formData.amount} onChange={(e) => setFormData({ ...formData, amount: e.target.value })} placeholder="Enter payment amount" />
                                </div>

                                <div>
                                    <label className="text-xs text-[#A0A0A0] block mb-1.5">Category</label>
                                    <Select value={formData.category} onValueChange={(value) => setFormData({ ...formData, category: value })}>
                                        <SelectTrigger className="bg-[#1A1A1A] border-[#2A2A2A] text-white">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                            <SelectItem value="professional" className="text-white focus:bg-[#2A2A2A]">Professional Fees (194J)</SelectItem>
                                            <SelectItem value="contract" className="text-white focus:bg-[#2A2A2A]">Contractor (194C)</SelectItem>
                                            <SelectItem value="rent" className="text-white focus:bg-[#2A2A2A]">Rent (194I)</SelectItem>
                                            <SelectItem value="commission" className="text-white focus:bg-[#2A2A2A]">Commission (194H)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div>
                                    <label className="text-xs text-[#A0A0A0] block mb-1.5">Payee Type</label>
                                    <Select value={formData.isIndividual} onValueChange={(value) => setFormData({ ...formData, isIndividual: value })}>
                                        <SelectTrigger className="bg-[#1A1A1A] border-[#2A2A2A] text-white">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                            <SelectItem value="true" className="text-white focus:bg-[#2A2A2A]">Individual / HUF</SelectItem>
                                            <SelectItem value="false" className="text-white focus:bg-[#2A2A2A]">Company / Firm</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <button onClick={onCalculate} disabled={!formData.amount} className="mo-btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-40">
                                    <Calculator className="h-4 w-4" /> Calculate TDS
                                </button>

                                {calcResult && (
                                    <div className="rounded-xl border border-[#4CBB1740] p-4" style={{ backgroundColor: "#4CBB1710" }}>
                                        <h4 className="font-semibold text-white mb-3">Calculation Result</h4>
                                        <div className="flex flex-col gap-2 text-sm">
                                            <div className="flex justify-between"><span className="text-[#A0A0A0]">Section:</span><span className="font-semibold text-white">{calcResult.section}</span></div>
                                            <div className="flex justify-between"><span className="text-[#A0A0A0]">Rate:</span><span className="font-semibold text-white">{calcResult.rate}%</span></div>
                                            <div className="flex justify-between pt-2 border-t border-[#2A2A2A]">
                                                <span className="text-[#A0A0A0]">TDS to Deduct:</span>
                                                <span className="font-bold text-lg text-[#4CBB17]">INR {calcResult.deductible}</span>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div>
                                <h3 className="font-semibold text-white mb-3">Outstanding TDS Liabilities</h3>
                                <div className="flex flex-col items-center justify-center h-48 rounded-xl border border-dashed border-[#2A2A2A] text-center">
                                    <CheckCircle2 className="h-10 w-10 text-[#4CBB17] mb-2" style={{ opacity: 0.4 }} />
                                    <p className="text-[#A0A0A0] text-sm">Use the calculator to estimate current TDS deductions.</p>
                                    <p className="text-xs text-[#A0A0A0] mt-1">The result updates from live form inputs and backend tax logic.</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === "documents" && (
                        <div className="grid gap-6 md:grid-cols-2">
                            <div>
                                <h3 className="font-semibold text-white mb-3">Audit Readiness Checklist</h3>
                                <div className="flex flex-col gap-3">
                                    {(auditData.checklist || []).map((item, index) => (
                                        <div key={index} className="flex items-center justify-between p-4 rounded-xl border border-[#2A2A2A] bg-[#1A1A1A]">
                                            <div className="flex items-center gap-3">
                                                {item.status === "pass"
                                                    ? <CheckCircle2 className="h-5 w-5 text-[#4CBB17]" />
                                                    : <AlertCircle className="h-5 w-5 text-[#FFB300]" />}
                                                <span className="text-sm font-medium text-white">{item.item}</span>
                                            </div>
                                            <span className="text-xs text-[#A0A0A0]">{item.completion}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="flex flex-col gap-4">
                                <div className="mo-card !bg-[#1A1A1A]">
                                    <h3 className="font-semibold text-white mb-2 text-sm">Readiness Score</h3>
                                    <p className="text-3xl font-bold text-[#4CBB17]">{auditData.auditReadinessScore || auditData.audit_readiness_score || 85}%</p>
                                    <p className="text-xs text-[#A0A0A0] mt-1">{auditData.message || "Ready for upcoming audits"}</p>
                                </div>
                                <div className="rounded-xl border border-dashed border-[#2A2A2A] p-6 text-center">
                                    <FileText className="h-10 w-10 text-[#2A2A2A] mx-auto mb-3" />
                                    <p className="text-sm text-[#A0A0A0]">Additional Documents</p>
                                    <button
                                        onClick={() => exportJson(`audit-readiness-${new Date().toISOString().slice(0, 10)}.json`, auditData)}
                                        className="mo-btn-secondary text-xs mt-3 flex items-center gap-2 mx-auto"
                                    >
                                        <Download className="h-3 w-3" /> Export Ledger
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
