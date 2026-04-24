import { useState, useEffect } from "react";
import { TrendingUp, TrendingDown, AlertTriangle, Calendar, Loader2, Plus } from "lucide-react";
import { useAuth } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { toast } from "sonner";

const PRIORITY_BADGE = {
    high: "bg-[#CD1C1820] text-[#CD1C18] border-[#CD1C1840]",
    medium: "bg-[#FFB30020] text-[#FFB300] border-[#FFB30040]",
    low: "bg-[#A0A0A020] text-[#A0A0A0] border-[#A0A0A040]",
};

export default function CashflowPage() {
    const { getToken } = useAuth();
    const { userId: internalUserId, orgId: internalOrgId, loading: onboardingLoading } = useOnboardingStatus();
    
    const [loading, setLoading] = useState(true);
    const [generatingForecast, setGeneratingForecast] = useState(false);
    const [schedulingPayment, setSchedulingPayment] = useState(false);
    const [showModal, setShowModal] = useState(false);
    
    const [summary, setSummary] = useState(null);
    const [chartData, setChartData] = useState([]);
    
    const [paymentForm, setPaymentForm] = useState({
        invoiceId: "",
        scheduledDate: "",
        amount: "",
        paymentMethod: "Bank Transfer",
        notes: ""
    });

    useEffect(() => {
        if (!onboardingLoading && internalUserId && internalOrgId) {
            fetchSummary();
        }
    }, [onboardingLoading, internalUserId, internalOrgId]);

    async function fetchSummary() {
        setLoading(true);
        try {
            const token = await getToken();
            const res = await fetch(`/api/cashflow/summary?orgId=${internalOrgId}&months=6`, {
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId,
                }
            });
            if (!res.ok) throw new Error("Failed to fetch cashflow summary");
            const data = await res.json();
            setSummary(data);
            setChartData(data.monthly);
        } catch (error) {
            console.error(error);
            toast.error("Failed to load cashflow data");
        } finally {
            setLoading(false);
        }
    }

    async function handleGenerateForecast() {
        setGeneratingForecast(true);
        try {
            const token = await getToken();
            const res = await fetch(`/api/cashflow/forecast?orgId=${internalOrgId}&months=3`, {
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId,
                }
            });
            if (!res.ok) throw new Error("Failed to generate forecast");
            const data = await res.json();
            
            // Append forecast to chart data
            const newChartData = [...(summary?.monthly || [])];
            data.forecast.forEach(f => {
                newChartData.push({
                    month: f.month,
                    predictedIncome: f.predictedIncome,
                    predictedExpense: f.predictedExpense,
                    isForecast: true
                });
            });
            setChartData(newChartData);
            toast.success("Forecast generated based on moving averages & pending invoices");
        } catch (error) {
            console.error(error);
            toast.error("Failed to generate forecast");
        } finally {
            setGeneratingForecast(false);
        }
    }

    async function handleSchedulePayment(e) {
        e.preventDefault();
        setSchedulingPayment(true);
        try {
            const token = await getToken();
            const res = await fetch("/api/payments/schedule", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId,
                },
                body: JSON.stringify({
                    orgId: internalOrgId,
                    ...paymentForm
                })
            });
            if (!res.ok) throw new Error("Failed to schedule payment");
            toast.success("Payment scheduled successfully");
            setShowModal(false);
            setPaymentForm({ invoiceId: "", scheduledDate: "", amount: "", paymentMethod: "Bank Transfer", notes: "" });
            fetchSummary(); // refresh data
        } catch (error) {
            console.error(error);
            toast.error("Failed to schedule payment");
        } finally {
            setSchedulingPayment(false);
        }
    }

    if (loading || onboardingLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Cash Flow</h1>
                    <p className="mo-text-secondary mt-1">Monitor and forecast your business cashflow</p>
                </div>
                <div className="flex gap-2">
                    <button onClick={() => setShowModal(true)} className="mo-btn-secondary flex items-center gap-2">
                        <Calendar className="h-4 w-4" /> Schedule Payments
                    </button>
                    <button onClick={handleGenerateForecast} disabled={generatingForecast} className="mo-btn-primary flex items-center gap-2 disabled:opacity-50">
                        {generatingForecast ? <Loader2 className="h-4 w-4 animate-spin" /> : <TrendingUp className="h-4 w-4" />} 
                        Generate Forecast
                    </button>
                </div>
            </div>

            {/* ── Summary Stats ─────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-4">
                <div className="mo-stat-card border border-[#4CBB1740] bg-[#4CBB1710]">
                    <span className="text-xs text-[#A0A0A0] uppercase tracking-wide">Net Cashflow</span>
                    <p className="text-2xl font-bold text-[#4CBB17] mt-1">₹{summary?.netCashflow?.toLocaleString() ?? 0}</p>
                </div>
                <div className="mo-stat-card border border-[#2A2A2A]">
                    <span className="text-xs text-[#A0A0A0] uppercase tracking-wide">Total Income</span>
                    <p className="text-2xl font-bold text-white mt-1">₹{summary?.totalIncome?.toLocaleString() ?? 0}</p>
                </div>
                <div className="mo-stat-card border border-[#2A2A2A]">
                    <span className="text-xs text-[#A0A0A0] uppercase tracking-wide">Total Expense</span>
                    <p className="text-2xl font-bold text-[#CD1C18] mt-1">₹{summary?.totalExpense?.toLocaleString() ?? 0}</p>
                </div>
                <div className="mo-stat-card border border-[#2A2A2A]">
                    <span className="text-xs text-[#A0A0A0] uppercase tracking-wide">Running Balance</span>
                    <p className="text-2xl font-bold text-[#60A5FA] mt-1">₹{summary?.runningBalance?.toLocaleString() ?? 0}</p>
                </div>
            </div>

            {/* ── Chart ───────────────────────────────────────────────────────── */}
            <div className="mo-card">
                <h2 className="font-semibold text-white mb-4">Cashflow Trend & Forecast</h2>
                <div className="h-80 w-full text-xs">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                            <defs>
                                <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#4CBB17" stopOpacity={0.3}/>
                                    <stop offset="95%" stopColor="#4CBB17" stopOpacity={0}/>
                                </linearGradient>
                                <linearGradient id="colorExpense" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#CD1C18" stopOpacity={0.3}/>
                                    <stop offset="95%" stopColor="#CD1C18" stopOpacity={0}/>
                                </linearGradient>
                                <linearGradient id="colorPredIncome" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#60A5FA" stopOpacity={0.3}/>
                                    <stop offset="95%" stopColor="#60A5FA" stopOpacity={0}/>
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#2A2A2A" vertical={false} />
                            <XAxis dataKey="month" stroke="#A0A0A0" tick={{ fill: "#A0A0A0" }} />
                            <YAxis stroke="#A0A0A0" tick={{ fill: "#A0A0A0" }} />
                            <Tooltip 
                                contentStyle={{ backgroundColor: "#111", borderColor: "#2A2A2A", borderRadius: "8px" }}
                                itemStyle={{ color: "#fff" }}
                            />
                            <Legend />
                            <Area type="monotone" dataKey="income" stroke="#4CBB17" fillOpacity={1} fill="url(#colorIncome)" name="Actual Income" />
                            <Area type="monotone" dataKey="expense" stroke="#CD1C18" fillOpacity={1} fill="url(#colorExpense)" name="Actual Expense" />
                            <Area type="monotone" dataKey="predictedIncome" stroke="#60A5FA" strokeDasharray="5 5" fillOpacity={1} fill="url(#colorPredIncome)" name="Predicted Income" />
                            <Area type="monotone" dataKey="predictedExpense" stroke="#FFB300" strokeDasharray="5 5" fillOpacity={0} name="Predicted Expense" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* ── Pending Invoices & Alerts ──────────────────────────────────── */}
            <div className="grid gap-6 md:grid-cols-2">
                <div className="mo-card">
                    <div className="flex items-center gap-2 mb-4">
                        <TrendingUp className="h-5 w-5 text-[#4CBB17]" />
                        <div>
                            <h2 className="mo-h2">Pending Receivables</h2>
                            <p className="mo-text-secondary">Total amount waiting to be paid to you</p>
                        </div>
                    </div>
                    <div className="p-4 rounded-xl border border-[#4CBB1740] bg-[#4CBB1710] flex items-center justify-between">
                        <span className="font-semibold text-white">Pending Invoices</span>
                        <span className="font-bold text-[#4CBB17] text-xl">₹{summary?.pendingInvoicesTotal?.toLocaleString() ?? 0}</span>
                    </div>
                </div>

                <div className="mo-card">
                    <div className="flex items-center gap-2 mb-4">
                        <AlertTriangle className="h-5 w-5 text-[#CD1C18]" />
                        <div>
                            <h2 className="mo-h2">Overdue Payables</h2>
                            <p className="mo-text-secondary">Amount that is overdue for collection</p>
                        </div>
                    </div>
                    <div className="p-4 rounded-xl border border-[#CD1C1840] bg-[#CD1C1810] flex items-center justify-between">
                        <span className="font-semibold text-white">Overdue Invoices</span>
                        <span className="font-bold text-[#CD1C18] text-xl">₹{summary?.overdueInvoicesTotal?.toLocaleString() ?? 0}</span>
                    </div>
                </div>
            </div>

            {/* ── Schedule Payment Modal ──────────────────────────────────────── */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-[#111] border border-[#2A2A2A] rounded-2xl w-full max-w-md p-6">
                        <h2 className="text-xl font-bold text-white mb-1">Schedule Payment</h2>
                        <p className="text-sm text-[#A0A0A0] mb-5">Set up an upcoming outgoing payment to update your forecast.</p>
                        
                        <form onSubmit={handleSchedulePayment} className="space-y-4">
                            <div>
                                <label className="block text-xs text-[#A0A0A0] mb-1.5">Description / Notes</label>
                                <input 
                                    required 
                                    value={paymentForm.notes} 
                                    onChange={e => setPaymentForm({...paymentForm, notes: e.target.value})}
                                    className="w-full bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg px-3 py-2 text-white text-sm focus:border-[#4CBB17] outline-none" 
                                    placeholder="e.g. Office Rent for May"
                                />
                            </div>
                            
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs text-[#A0A0A0] mb-1.5">Amount (INR)</label>
                                    <input 
                                        required 
                                        type="number" 
                                        value={paymentForm.amount} 
                                        onChange={e => setPaymentForm({...paymentForm, amount: e.target.value})}
                                        className="w-full bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg px-3 py-2 text-white text-sm focus:border-[#4CBB17] outline-none" 
                                        placeholder="5000"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-[#A0A0A0] mb-1.5">Date</label>
                                    <input 
                                        required 
                                        type="date" 
                                        value={paymentForm.scheduledDate} 
                                        onChange={e => setPaymentForm({...paymentForm, scheduledDate: e.target.value})}
                                        className="w-full bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg px-3 py-2 text-white text-sm focus:border-[#4CBB17] outline-none" 
                                    />
                                </div>
                            </div>

                            <div className="flex gap-3 pt-4">
                                <button type="button" onClick={() => setShowModal(false)} className="flex-1 mo-btn-secondary">
                                    Cancel
                                </button>
                                <button type="submit" disabled={schedulingPayment} className="flex-1 mo-btn-primary flex justify-center items-center gap-2">
                                    {schedulingPayment ? <Loader2 className="h-4 w-4 animate-spin" /> : "Schedule"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
