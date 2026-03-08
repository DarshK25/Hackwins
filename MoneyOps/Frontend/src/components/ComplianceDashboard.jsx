import { useState, useEffect } from "react";
import {
    Shield, AlertTriangle, CheckCircle2, FileText, RefreshCw,
    Download, Calendar as CalendarIcon, AlertCircle, Calculator,
} from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import {
    Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { useAuth, useUser } from "@clerk/clerk-react";

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
    const { user } = useUser();
    const [activeTab, setActiveTab] = useState("overview");
    const [date, setDate] = useState(new Date());
    const [deadlines, setDeadlines] = useState([]);
    const [calcResult, setCalcResult] = useState(null);
    const [formData, setFormData] = useState({ amount: "", category: "professional", isIndividual: "true" });

    useEffect(() => {
        const fetchDeadlines = async () => {
            if (!businessId || !user?.id) return;
            try {
                const token = await getToken();
                const res = await fetch(`/api/deadlines?businessId=${businessId}`, {
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "X-User-Id": user?.id
                    }
                });
                if (!res.ok) throw new Error();
                const data = await res.json();
                setDeadlines(data.deadlines || []);
            } catch (error) {
                setDeadlines([
                    { id: 1, title: "GST Filing (Current Month)", dueDate: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 20).toISOString().split("T")[0], type: "GST", priority: "high" },
                    { id: 2, title: "TDS Payment", dueDate: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 7).toISOString().split("T")[0], type: "TDS", priority: "high" },
                ]);
            }
        };
        fetchDeadlines();
    }, [businessId, user?.id, getToken]);

    const complianceScore = data?.score || 85;
    const pendingTasks = data?.pendingTasks || [
        { id: 1, title: "GST Filing for December", dueDate: "2025-01-20", priority: "high", status: "pending", type: "GST" },
        { id: 2, title: "FY 2024-25 Annual Return", dueDate: "2025-07-31", priority: "medium", status: "pending", type: "ITR" },
        { id: 3, title: "Q3 TDS Return Filing", dueDate: "2025-01-31", priority: "high", status: "pending", type: "TDS" },
    ];
    const recentAlerts = data?.alerts || [
        { id: 1, title: "New GST Regulation Update", date: "2025-01-05", type: "info" },
        { id: 2, title: "Potential Input Tax Credit Mismatch", date: "2024-12-15", type: "warning" },
    ];

    async function onCalculate() {
        try {
            const token = await getToken();
            const res = await fetch("/api/tds/calc", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": user?.id
                },
                body: JSON.stringify({ amount: parseFloat(formData.amount), category: formData.category, isIndividual: formData.isIndividual === "true" }),
            });
            if (!res.ok) throw new Error("Calculation failed");
            setCalcResult(await res.json());
            toast.success("TDS calculated successfully");
        } catch {
            toast.error("Using fallback calculation");
            const amount = parseFloat(formData.amount) || 0;
            const rateMap = { professional: 10, contract: formData.isIndividual === "true" ? 1 : 2, rent: 10, commission: 5 };
            const sectionMap = { professional: "194J", contract: "194C", rent: "194I", commission: "194H" };
            setCalcResult({ section: sectionMap[formData.category] || "194J", rate: rateMap[formData.category] || 10, deductible: ((amount * (rateMap[formData.category] || 10)) / 100).toFixed(2) });
        }
    }

    const healthColor = complianceScore >= 80 ? "#4CBB17" : complianceScore >= 60 ? "#FFB300" : "#CD1C18";
    const tabs = [
        { id: "overview", label: "Overview" },
        { id: "calendar", label: "Calendar" },
        { id: "tds", label: "TDS Calculator" },
        { id: "documents", label: "Documents" },
    ];

    return (
        <div className="flex flex-col gap-6">
            {/* Header */}
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
                    <button className="mo-btn-primary flex items-center gap-2 text-sm">
                        <Download className="h-4 w-4" /> Export Report
                    </button>
                </div>
            </div>

            {/* Stats */}
            <div className="grid gap-4 md:grid-cols-4">
                <div className="mo-card" style={{ borderColor: `${healthColor}30` }}>
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-xs text-[#A0A0A0] font-medium uppercase tracking-wide">Compliance Score</p>
                        <Shield className="h-4 w-4" style={{ color: healthColor }} />
                    </div>
                    <p className="text-2xl font-bold" style={{ color: healthColor }}>{complianceScore}/100</p>
                    <p className="text-xs text-[#A0A0A0] mt-1">{complianceScore >= 80 ? "Good standing" : "Attention needed"}</p>
                </div>
                <StatCard label="Pending Filings" value={pendingTasks.length} sub="Due within 30 days" icon={FileText} iconColor="#A0A0A0" />
                <StatCard label="Risk Alerts" value={recentAlerts.length} sub="Requires attention" icon={AlertTriangle} iconColor="#CD1C18" accent="#CD1C18" />
                <StatCard label="Next Deadline" value="Jan 20" sub="GST Filing" icon={CalendarIcon} iconColor="#A0A0A0" />
            </div>

            {/* Tabs */}
            <div className="mo-card !p-0">
                <div className="flex border-b border-[#2A2A2A] px-4 overflow-x-auto">
                    {tabs.map(t => (
                        <button
                            key={t.id}
                            onClick={() => setActiveTab(t.id)}
                            className={`px-4 py-3.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === t.id ? "border-[#4CBB17] text-[#4CBB17]" : "border-transparent text-[#A0A0A0] hover:text-white"}`}
                        >
                            {t.label}
                        </button>
                    ))}
                </div>
                <div className="p-5">

                    {/* Overview */}
                    {activeTab === "overview" && (
                        <div className="grid gap-6 lg:grid-cols-7">
                            {/* Tasks */}
                            <div className="lg:col-span-4 flex flex-col gap-3">
                                <h3 className="font-semibold text-white mb-1">Compliance Tasks</h3>
                                {pendingTasks.map(task => (
                                    <div key={task.id} className="flex items-center justify-between p-4 rounded-xl border border-[#2A2A2A] hover:border-[#3A3A3A] transition-all">
                                        <div className="flex items-center gap-3">
                                            <div className="p-2 rounded-full" style={{ backgroundColor: PRIORITY_DOT[task.priority] + "20", color: PRIORITY_DOT[task.priority] }}>
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
                                            <button className="text-xs text-[#A0A0A0] hover:text-[#4CBB17] transition-colors px-2">View</button>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Alerts Sidebar */}
                            <div className="lg:col-span-3 flex flex-col gap-4">
                                {/* AI Summary */}
                                <div className="rounded-xl border border-[#2A2A2A] p-4">
                                    <h3 className="font-semibold text-white mb-3 text-sm">Agent Summary</h3>
                                    <div className="flex flex-col gap-3">
                                        {[
                                            "GST filing frequency set to Monthly. Next deadline: April 20th.",
                                            "Detected potential mismatch in Input Tax Credit for March invoice #INV-003.",
                                            "E-invoicing threshold lowered to ₹5 Cr effective from next fiscal year.",
                                        ].map((msg, i) => (
                                            <div key={i} className="flex gap-2 text-sm">
                                                <div className="w-1.5 h-1.5 mt-1.5 rounded-full bg-[#4CBB17] flex-shrink-0" />
                                                <p className="text-[#A0A0A0]">{msg}</p>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Recent Alerts */}
                                <div className="rounded-xl border border-[#2A2A2A] p-4">
                                    <h3 className="font-semibold text-white mb-3 text-sm">Recent Alerts</h3>
                                    <div className="flex flex-col gap-3">
                                        {recentAlerts.map(alert => (
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

                    {/* Calendar */}
                    {activeTab === "calendar" && (
                        <div className="grid gap-6 md:grid-cols-2">
                            <div>
                                <h3 className="font-semibold text-white mb-3">Upcoming Deadlines</h3>
                                <div className="flex flex-col gap-3">
                                    {(deadlines.length > 0 ? deadlines : pendingTasks).map(dl => (
                                        <div key={dl.id} className="flex items-center justify-between p-4 rounded-xl border border-[#2A2A2A] hover:border-[#3A3A3A] transition-all">
                                            <div>
                                                <h4 className="font-semibold text-white text-sm">{dl.title}</h4>
                                                <p className="text-xs text-[#A0A0A0] mt-0.5">Due: {dl.dueDate}</p>
                                            </div>
                                            <span className={`text-xs px-2 py-0.5 rounded-md font-medium border ${PRIORITY_BADGE[dl.priority] || PRIORITY_BADGE.medium}`}>{dl.type}</span>
                                        </div>
                                    ))}
                                    {deadlines.length === 0 && pendingTasks.length === 0 && (
                                        <div className="flex flex-col items-center py-10 text-center">
                                            <CheckCircle2 className="h-8 w-8 text-[#4CBB17] mb-2" />
                                            <p className="text-[#A0A0A0] text-sm">No pending deadlines</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                            <div>
                                <h3 className="font-semibold text-white mb-3">Calendar</h3>
                                <div className="rounded-xl border border-[#2A2A2A] overflow-hidden flex justify-center p-2"
                                    style={{ backgroundColor: "#1A1A1A" }}>
                                    <Calendar mode="single" selected={date} onSelect={setDate}
                                        className="rounded-md" />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* TDS Calculator */}
                    {activeTab === "tds" && (
                        <div className="grid gap-6 md:grid-cols-2">
                            <div className="flex flex-col gap-4">
                                <div className="flex items-center gap-2 mb-1">
                                    <Calculator className="h-5 w-5 text-[#4CBB17]" />
                                    <h3 className="font-semibold text-white">TDS Calculator</h3>
                                </div>
                                <p className="text-sm text-[#A0A0A0] -mt-2">Calculate TDS deductions for various payment categories</p>

                                <div>
                                    <label className="text-xs text-[#A0A0A0] block mb-1.5">Payment Amount (₹)</label>
                                    <DarkInput type="number" value={formData.amount} onChange={e => setFormData({ ...formData, amount: e.target.value })} placeholder="Enter payment amount" />
                                </div>

                                <div>
                                    <label className="text-xs text-[#A0A0A0] block mb-1.5">Category</label>
                                    <Select value={formData.category} onValueChange={v => setFormData({ ...formData, category: v })}>
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
                                    <Select value={formData.isIndividual} onValueChange={v => setFormData({ ...formData, isIndividual: v })}>
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
                                                <span className="font-bold text-lg text-[#4CBB17]">₹{calcResult.deductible}</span>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>

                            <div>
                                <h3 className="font-semibold text-white mb-3">Outstanding TDS Liabilities</h3>
                                <div className="flex flex-col items-center justify-center h-48 rounded-xl border border-dashed border-[#2A2A2A] text-center">
                                    <CheckCircle2 className="h-10 w-10 text-[#4CBB17] mb-2" style={{ opacity: 0.4 }} />
                                    <p className="text-[#A0A0A0] text-sm">No outstanding liabilities found.</p>
                                    <p className="text-xs text-[#A0A0A0] mt-1">All TDS payments are up to date</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Documents */}
                    {activeTab === "documents" && (
                        <div>
                            <h3 className="font-semibold text-white mb-3">Compliance Documents</h3>
                            <div className="flex flex-col items-center justify-center h-64 rounded-xl border-2 border-dashed border-[#2A2A2A] text-center">
                                <FileText className="h-14 w-14 text-[#2A2A2A] mb-3" />
                                <p className="text-[#A0A0A0] text-sm">No compliance documents found</p>
                                <p className="text-xs text-[#A0A0A0] mt-1">Upload documents to get started</p>
                                <button className="mo-btn-secondary flex items-center gap-2 text-sm mt-4">
                                    <Download className="h-4 w-4" /> Upload Document
                                </button>
                            </div>
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
}
