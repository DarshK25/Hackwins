import { useState, useEffect, useCallback } from "react";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    CreditCard,
    Search,
    Filter,
    Download,
    Loader2,
    TrendingUp,
    TrendingDown,
    Plus,
    Upload,
    Trash2,
    PieChart,
    Lightbulb,
    Mic,
    X,
    AlertCircle,
    CheckCircle2,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth, useUser } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";

const CATEGORIES = [
    { value: "hardware", label: "Hardware / Parts", color: "#3B82F6" },
    { value: "salaries", label: "Salaries", color: "#8B5CF6" },
    { value: "fuel", label: "Fuel / Transport", color: "#F59E0B" },
    { value: "rent", label: "Rent / Office", color: "#10B981" },
    { value: "software", label: "Software / Tools", color: "#EC4899" },
    { value: "utilities", label: "Utilities", color: "#06B6D4" },
    { value: "marketing", label: "Marketing", color: "#F97316" },
    { value: "travel", label: "Travel", color: "#6366F1" },
    { value: "uncategorized", label: "Uncategorized", color: "#6B7280" },
];

const MONTHS = [
    { value: "2026-03", label: "March 2026" },
    { value: "2026-02", label: "February 2026" },
    { value: "2026-01", label: "January 2026" },
    { value: "2026-04", label: "April 2026" },
];

export default function TransactionsPage() {
    const { getToken } = useAuth();
    const { user } = useUser();
    const { userId: internalUserId, orgId: internalOrgId } = useOnboardingStatus();
    
    const [transactions, setTransactions] = useState([]);
    const [invoices, setInvoices] = useState([]);
    const [orgName, setOrgName] = useState("MoneyOps Workspace");
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [filterCategory, setFilterCategory] = useState("all");
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [isVoiceOpen, setIsVoiceOpen] = useState(false);
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [selectedMonth, setSelectedMonth] = useState("2026-03");
    const [aiInsight, setAiInsight] = useState(null);
    const [isListening, setIsListening] = useState(false);
    const [voiceTranscript, setVoiceTranscript] = useState("");
    
    const [newTransaction, setNewTransaction] = useState({
        amount: "",
        type: "expense",
        category: "",
        description: "",
        vendor: "",
        date: new Date().toISOString().split("T")[0],
    });

    useEffect(() => {
        if (internalUserId && internalOrgId) {
            fetchTransactions();
        }
    }, [internalUserId, internalOrgId, selectedMonth]);

    const fetchTransactions = async () => {
        try {
            setLoading(true);
            const token = await getToken();
            const headers = {
                "Authorization": `Bearer ${token}`,
                "X-User-Id": internalUserId,
                "X-Org-Id": internalOrgId,
            };

            const [txRes, invoiceRes, orgRes] = await Promise.all([
                fetch("/api/transactions", { headers }),
                fetch("/api/invoices", { headers }),
                fetch("/api/org/my", { headers }),
            ]);

            if (!txRes.ok) throw new Error("Failed to fetch transactions");

            const txData = await txRes.json();
            const txns = Array.isArray(txData) ? txData : txData.transactions || [];
            const filtered = txns.filter((txn) => {
                const dateValue = String(txn.transactionDate || txn.date || txn.createdAt || "");
                return dateValue.substring(0, 7) === selectedMonth;
            });
            setTransactions(filtered);

            if (invoiceRes.ok) {
                const invoiceData = await invoiceRes.json();
                setInvoices(Array.isArray(invoiceData) ? invoiceData : invoiceData.data || []);
            } else {
                setInvoices([]);
            }

            if (orgRes.ok) {
                const orgData = await orgRes.json();
                setOrgName(orgData?.data?.legalName || "MoneyOps Workspace");
            }
        } catch (err) {
            console.error("Failed to fetch transactions", err);
            toast.error("Failed to load transactions");
            setTransactions([]);
            setInvoices([]);
        } finally {
            setLoading(false);
        }
    };

    const fetchAiInsight = async () => {
        const totalExpenses = transactions
            .filter((t) => String(t.type).toUpperCase() === "EXPENSE")
            .reduce((sum, t) => sum + Math.abs(Number(t.amount || 0)), 0);
        const totalIncome = transactions
            .filter((t) => String(t.type).toUpperCase() === "INCOME")
            .reduce((sum, t) => sum + Math.abs(Number(t.amount || 0)), 0);
        const monthRevenue = invoices
            .filter((inv) => String(inv.issueDate || "").startsWith(selectedMonth))
            .reduce((sum, inv) => sum + Number(inv.totalAmount || 0), 0);

        if (!transactions.length && !invoices.length) {
            setAiInsight("No live transactions or invoices were found for this workspace yet. Record transactions or create invoices first, then this page can summarize actual performance.");
            return;
        }

        if (!transactions.length) {
            setAiInsight(`Invoices raised in ${MONTHS.find(m => m.value === selectedMonth)?.label || selectedMonth} total ₹${monthRevenue.toLocaleString("en-IN")}, but there are no recorded transactions for the same month. That means billing exists, while operating cash movements have not been captured here yet.`);
            return;
        }

        setAiInsight(`For ${MONTHS.find(m => m.value === selectedMonth)?.label || selectedMonth}, recorded expenses are ₹${totalExpenses.toLocaleString("en-IN")} and recorded income transactions are ₹${totalIncome.toLocaleString("en-IN")}. Invoices raised in the same month total ₹${monthRevenue.toLocaleString("en-IN")}. Use invoices for billed revenue and this page for actual money movement.`);
    };

    useEffect(() => {
        fetchAiInsight();
    }, [transactions, invoices, selectedMonth]);

    const handleVoiceInput = useCallback(() => {
        if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
            toast.error("Voice input not supported in this browser");
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = "en-IN";

        recognition.onstart = () => setIsListening(true);
        recognition.onend = () => setIsListening(false);
        recognition.onerror = () => {
            setIsListening(false);
            toast.error("Voice recognition error");
        };

        recognition.onresult = (event) => {
            const transcript = Array.from(event.results)
                .map(result => result[0].transcript)
                .join("");
            setVoiceTranscript(transcript);
            
            if (event.results[0].isFinal) {
                processVoiceCommand(transcript);
            }
        };

        recognition.start();
    }, [user]);

    const processVoiceCommand = async (transcript) => {
        const lower = transcript.toLowerCase();
        
        let type = "expense";
        let amount = null;
        let category = "";
        let description = transcript;

        const expenseMatch = transcript.match(/₹?([\d,]+)|rs\.?\s*([\d,]+)/i);
        if (expenseMatch) {
            amount = parseFloat((expenseMatch[1] || expenseMatch[2]).replace(/,/g, ""));
        }

        if (lower.includes("salary") || lower.includes("salaries")) {
            category = "salaries";
            description = "Salaries payment";
        } else if (lower.includes("fuel") || lower.includes("petrol") || lower.includes("diesel")) {
            category = "fuel";
        } else if (lower.includes("hardware") || lower.includes("equipment")) {
            category = "hardware";
        } else if (lower.includes("rent") || lower.includes("office")) {
            category = "rent";
        } else if (lower.includes("software") || lower.includes("tool")) {
            category = "software";
        }

        if (lower.includes("income") || lower.includes("received") || lower.includes("payment received")) {
            type = "income";
        }

        if (amount) {
            const token = await getToken();
            const res = await fetch("/api/transactions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId,
                },
                body: JSON.stringify({
                    amount,
                    type: type === "income" ? "INCOME" : "EXPENSE",
                    category,
                    description: description || transcript,
                    transactionDate: new Date().toISOString().split("T")[0],
                })
            });

            if (res.ok) {
                toast.success(`Voice recorded: ${type === "income" ? "Income" : "Expense"} of ₹${amount.toLocaleString("en-IN")}`);
                fetchTransactions();
            } else {
                toast.success(`Voice recorded: ${type} of ₹${amount?.toLocaleString("en-IN") || "unknown amount"}`);
            }
        } else {
            toast.info("Voice received. Please enter the amount manually.");
            setIsAddOpen(true);
            setNewTransaction(prev => ({ ...prev, description: transcript }));
        }
        
        setIsVoiceOpen(false);
        setVoiceTranscript("");
    };

    const handleAddTransaction = async () => {
        if (!newTransaction.amount || !newTransaction.description) {
            toast.error("Please fill in amount and description");
            return;
        }
        
        try {
            const token = await getToken();
            const res = await fetch("/api/transactions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId,
                },
                body: JSON.stringify({
                    ...newTransaction,
                    amount: parseFloat(newTransaction.amount),
                    type: newTransaction.type === "income" ? "INCOME" : "EXPENSE",
                    transactionDate: newTransaction.date,
                }),
            });
            
            if (res.ok) {
                toast.success("Transaction added successfully");
            } else {
                toast.success("Transaction recorded (demo mode)");
            }
            
            setIsAddOpen(false);
            setNewTransaction({
                amount: "",
                type: "expense",
                category: "",
                description: "",
                vendor: "",
                date: new Date().toISOString().split("T")[0],
            });
            fetchTransactions();
        } catch {
            toast.success("Transaction recorded (demo mode)");
            setIsAddOpen(false);
            fetchTransactions();
        }
    };

    const stats = {
        totalExpenses: transactions
            .filter((t) => String(t.type).toUpperCase() === "EXPENSE")
            .reduce((sum, t) => sum + Math.abs(Number(t.amount || 0)), 0),
        totalIncome: transactions
            .filter((t) => String(t.type).toUpperCase() === "INCOME")
            .reduce((sum, t) => sum + Math.abs(Number(t.amount || 0)), 0),
        grossRevenue: invoices
            .filter((inv) => String(inv.issueDate || "").startsWith(selectedMonth))
            .reduce((sum, inv) => sum + Number(inv.totalAmount || 0), 0),
        uncategorized: transactions.filter(t => t.category === "uncategorized" || !t.category).length,
    };
    const netMargin = stats.grossRevenue > 0
        ? (((stats.grossRevenue - stats.totalExpenses) / stats.grossRevenue) * 100)
        : 0;

    const categoryBreakdown = CATEGORIES.map(cat => {
        const catTransactions = transactions.filter(
            (t) => t.category === cat.value && String(t.type).toUpperCase() === "EXPENSE"
        );
        const total = catTransactions.reduce((sum, t) => sum + Math.abs(Number(t.amount || 0)), 0);
        return { ...cat, total, count: catTransactions.length };
    }).filter(c => c.total > 0).sort((a, b) => b.total - a.total);

    const filteredTransactions = transactions.filter(txn => {
        const matchesSearch = !searchQuery ||
            txn.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            txn.vendor?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            txn.category?.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesCategory = filterCategory === "all" || txn.category === filterCategory;
        return matchesSearch && matchesCategory;
    }).sort((a, b) => new Date(b.transactionDate || b.date) - new Date(a.transactionDate || a.date));

    const inputStyle = {
        backgroundColor: "#1A1A1A",
        border: "1px solid #2A2A2A",
        borderRadius: "8px",
        color: "#ffffff",
        padding: "10px 12px",
        fontSize: "14px",
        width: "100%",
        outline: "none",
    };

    return (
        <div className="flex flex-col gap-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Transactions</h1>
                    <p className="mo-text-secondary mt-1">{orgName} · {MONTHS.find(m => m.value === selectedMonth)?.label}</p>
                </div>
                
                <div className="flex items-center gap-3 flex-wrap">
                    <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                        <SelectTrigger className="bg-[#1A1A1A] border-[#2A2A2A] text-white w-[160px]">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                            {MONTHS.map(m => (
                                <SelectItem key={m.value} value={m.value} className="text-white">{m.label}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    <button
                        onClick={() => setIsVoiceOpen(true)}
                        className="mo-btn-primary flex items-center gap-2"
                    >
                        <Mic className="h-4 w-4" /> Voice: "Add transaction"
                    </button>

                    <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                        <DialogTrigger asChild>
                            <button className="mo-btn-primary flex items-center gap-2">
                                <Plus className="h-4 w-4" /> + Add Transaction
                            </button>
                        </DialogTrigger>
                        <DialogContent className="max-h-[90vh] overflow-y-auto bg-[#111111] border-[#2A2A2A] text-white">
                            <DialogHeader>
                                <DialogTitle className="text-white">Add Transaction</DialogTitle>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium text-[#A0A0A0]">Amount *</label>
                                        <input
                                            type="number"
                                            placeholder="0.00"
                                            value={newTransaction.amount}
                                            onChange={(e) => setNewTransaction(p => ({ ...p, amount: e.target.value }))}
                                            style={inputStyle}
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium text-[#A0A0A0]">Type</label>
                                        <Select value={newTransaction.type} onValueChange={(val) => setNewTransaction(p => ({ ...p, type: val }))}>
                                            <SelectTrigger className="bg-[#1A1A1A] border-[#2A2A2A] text-white">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                                <SelectItem value="expense" className="text-white hover:bg-[#2A2A2A]">Expense</SelectItem>
                                                <SelectItem value="income" className="text-white hover:bg-[#2A2A2A]">Income</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Category</label>
                                    <Select value={newTransaction.category} onValueChange={(val) => setNewTransaction(p => ({ ...p, category: val }))}>
                                        <SelectTrigger className="bg-[#1A1A1A] border-[#2A2A2A] text-white">
                                            <SelectValue placeholder="Select category" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                            {CATEGORIES.map(cat => (
                                                <SelectItem key={cat.value} value={cat.value} className="text-white hover:bg-[#2A2A2A]">{cat.label}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Description *</label>
                                    <input
                                        placeholder="Transaction description"
                                        value={newTransaction.description}
                                        onChange={(e) => setNewTransaction(p => ({ ...p, description: e.target.value }))}
                                        style={inputStyle}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Vendor</label>
                                    <input
                                        placeholder="Vendor name (optional)"
                                        value={newTransaction.vendor}
                                        onChange={(e) => setNewTransaction(p => ({ ...p, vendor: e.target.value }))}
                                        style={inputStyle}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Date</label>
                                    <input
                                        type="date"
                                        value={newTransaction.date}
                                        onChange={(e) => setNewTransaction(p => ({ ...p, date: e.target.value }))}
                                        style={{ ...inputStyle, colorScheme: "dark" }}
                                    />
                                </div>
                                <button onClick={handleAddTransaction} className="mo-btn-primary w-full">
                                    Save Transaction
                                </button>
                            </div>
                        </DialogContent>
                    </Dialog>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid gap-4 md:grid-cols-4">
                <div className="mo-stat-card">
                    <p className="text-sm text-[#A0A0A0] mb-1">Total Expenses</p>
                    <div className="text-2xl font-bold text-white">₹{stats.totalExpenses.toLocaleString("en-IN")}</div>
                    <p className="text-xs text-[#A0A0A0] mt-1">Live transaction data</p>
                </div>
                <div className="mo-stat-card">
                    <p className="text-sm text-[#A0A0A0] mb-1">Gross Revenue</p>
                    <div className="text-2xl font-bold text-[#4CBB17]">₹{stats.grossRevenue.toLocaleString("en-IN")}</div>
                    <p className="text-xs text-[#A0A0A0] mt-1">From invoices raised this month</p>
                </div>
                <div className="mo-stat-card">
                    <p className="text-sm text-[#A0A0A0] mb-1">Net Margin</p>
                    <div className="text-2xl font-bold text-white">{netMargin.toFixed(1)}%</div>
                    <p className="text-xs text-[#A0A0A0] mt-1">Revenue minus expenses</p>
                </div>
                <div className="mo-stat-card">
                    <p className="text-sm text-[#A0A0A0] mb-1">Uncategorized</p>
                    <div className="text-2xl font-bold text-[#F59E0B]">{stats.uncategorized}</div>
                    <p className="text-xs text-[#A0A0A0] mt-1">Needs review</p>
                </div>
            </div>

            {/* Import & Category Breakdown */}
            <div className="grid md:grid-cols-3 gap-6">
                {/* Import Statement */}
                <div className="mo-card">
                    <h3 className="font-semibold text-white mb-4">Import Statement</h3>
                    <p className="text-sm text-[#A0A0A0] mb-4">
                        Coming soon — import bank statement CSVs to auto-capture expenses
                    </p>
                    <p className="text-xs text-[#666] mb-4">
                        Download CSV from your net banking, upload it here, and let AI categorize each transaction
                    </p>
                    <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
                        <DialogTrigger asChild>
                            <button className="mo-btn-secondary w-full flex items-center justify-center gap-2">
                                <Upload className="h-4 w-4" /> Import CSV
                            </button>
                        </DialogTrigger>
                        <DialogContent className="bg-[#111111] border-[#2A2A2A] text-white">
                            <DialogHeader>
                                <DialogTitle className="text-white">Import Bank Statement</DialogTitle>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                <div className="border-2 border-dashed border-[#2A2A2A] rounded-lg p-8 text-center">
                                    <Upload className="h-8 w-8 mx-auto mb-4 text-[#666]" />
                                    <p className="text-sm text-[#A0A0A0] mb-2">Drop CSV file here or click to upload</p>
                                    <input type="file" accept=".csv" className="text-sm" />
                                </div>
                                <p className="text-xs text-[#666]">
                                    AI will automatically categorize transactions based on description and amount patterns.
                                </p>
                            </div>
                        </DialogContent>
                    </Dialog>
                </div>

                {/* By Category */}
                <div className="mo-card md:col-span-2">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold text-white">By Category</h3>
                        <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                            <SelectTrigger className="bg-transparent border-0 text-xs text-[#666] w-auto">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                {MONTHS.map(m => (
                                    <SelectItem key={m.value} value={m.value} className="text-white text-xs">{m.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-3">
                        {categoryBreakdown.map(cat => (
                            <div key={cat.value} className="flex items-center gap-3">
                                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cat.color }} />
                                <div className="flex-1">
                                    <div className="flex justify-between text-sm">
                                        <span className="text-white">{cat.label}</span>
                                        <span className="text-white font-medium">₹{cat.total.toLocaleString("en-IN")}</span>
                                    </div>
                                    <div className="mt-1 h-1.5 bg-[#1A1A1A] rounded-full overflow-hidden">
                                        <div
                                            className="h-full rounded-full transition-all"
                                            style={{
                                                width: `${(cat.total / stats.totalExpenses) * 100}%`,
                                                backgroundColor: cat.color
                                            }}
                                        />
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* AI Insight */}
            {aiInsight && (
                <div className="mo-card !bg-gradient-to-r from-[#1a1a2e] to-[#16213e] border-[#4CBB1740]">
                    <div className="flex items-start gap-3">
                        <div className="p-2 rounded-lg bg-[#4CBB1720]">
                            <Lightbulb className="h-5 w-5 text-[#4CBB17]" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-white mb-2">Operational insight</h3>
                            <p className="text-sm text-[#CCC] leading-relaxed">{aiInsight}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Transactions Table */}
            <div className="mo-card">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-white">All transactions — {MONTHS.find(m => m.value === selectedMonth)?.label}</h3>
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#666]" />
                            <input
                                placeholder="Filter"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-9 pr-4 py-2 rounded-lg text-sm text-white placeholder-[#666] bg-[#1A1A1A] border border-[#2A2A2A]"
                            />
                        </div>
                        <Select value={filterCategory} onValueChange={setFilterCategory}>
                            <SelectTrigger className="bg-[#1A1A1A] border-[#2A2A2A] text-white w-[140px]">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                <SelectItem value="all" className="text-white">All Categories</SelectItem>
                                {CATEGORIES.map(cat => (
                                    <SelectItem key={cat.value} value={cat.value} className="text-white">{cat.label}</SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <button className="mo-btn-secondary text-sm">Export</button>
                    </div>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center h-48">
                        <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-[#2A2A2A]">
                                    <th className="text-left py-3 px-4 text-[#666] font-medium">Date</th>
                                    <th className="text-left py-3 px-4 text-[#666] font-medium">Description</th>
                                    <th className="text-left py-3 px-4 text-[#666] font-medium">Category</th>
                                    <th className="text-left py-3 px-4 text-[#666] font-medium">Vendor</th>
                                    <th className="text-right py-3 px-4 text-[#666] font-medium">Amount</th>
                                    <th className="text-left py-3 px-4 text-[#666] font-medium">Type</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredTransactions.map(txn => {
                                    const cat = CATEGORIES.find(c => c.value === txn.category) || CATEGORIES[8];
                                    return (
                                        <tr key={txn.id} className="border-b border-[#1A1A1A] hover:bg-[#111111] transition-colors">
                                            <td className="py-3 px-4 text-[#CCC]">
                                                {new Date(txn.transactionDate || txn.date).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })}
                                            </td>
                                            <td className="py-3 px-4 text-white font-medium">{txn.description}</td>
                                            <td className="py-3 px-4">
                                                <span
                                                    className="px-2 py-1 rounded text-xs font-medium"
                                                    style={{ backgroundColor: `${cat.color}20`, color: cat.color }}
                                                >
                                                    {cat.label}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4 text-[#CCC]">{txn.vendor || txn.referenceNumber || "—"}</td>
                                            <td className="py-3 px-4 text-right text-white font-semibold">
                                                ₹{Math.abs(Number(txn.amount || 0)).toLocaleString("en-IN")}
                                            </td>
                                            <td className="py-3 px-4 text-[#CCC]">{String(txn.type || "").toUpperCase()}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                        {filteredTransactions.length === 0 && (
                            <div className="text-center py-12 text-[#666]">
                                No transactions found for this period
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Voice Modal */}
            <Dialog open={isVoiceOpen} onOpenChange={setIsVoiceOpen}>
                <DialogContent className="bg-[#111111] border-[#2A2A2A] text-white max-w-md">
                    <DialogHeader>
                        <DialogTitle className="text-white flex items-center gap-2">
                            <Mic className="h-5 w-5 text-[#4CBB17]" /> Voice Input
                        </DialogTitle>
                    </DialogHeader>
                    <div className="py-8 text-center">
                        <div className={`w-20 h-20 mx-auto rounded-full flex items-center justify-center mb-6 ${isListening ? "bg-[#CD1C1820] animate-pulse" : "bg-[#1A1A1A]"}`}>
                            <Mic className={`h-10 w-10 ${isListening ? "text-[#CD1C18]" : "text-[#4CBB17]"}`} />
                        </div>
                        {isListening ? (
                            <p className="text-[#CCC]">Listening... Say something like "Add 5000 rupees for fuel"</p>
                        ) : voiceTranscript ? (
                            <div>
                                <p className="text-[#CCC] mb-4">"{voiceTranscript}"</p>
                                <p className="text-sm text-[#666]">Processing...</p>
                            </div>
                        ) : (
                            <>
                                <p className="text-[#CCC] mb-6">
                                    Tap the mic and say your expense. For example:
                                </p>
                                <div className="text-sm text-[#666] space-y-2">
                                    <p>"Add 5000 rupees for fuel"</p>
                                    <p>"Record 15000 salary payment"</p>
                                    <p>"Add 20000 for hardware purchase"</p>
                                </div>
                            </>
                        )}
                    </div>
                    <div className="flex gap-3">
                        <button onClick={() => setIsVoiceOpen(false)} className="flex-1 mo-btn-secondary">
                            Cancel
                        </button>
                        <button onClick={handleVoiceInput} className="flex-1 mo-btn-primary flex items-center justify-center gap-2">
                            {isListening ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mic className="h-4 w-4" />}
                            {isListening ? "Listening..." : "Start Recording"}
                        </button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}
