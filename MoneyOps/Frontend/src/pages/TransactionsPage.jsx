import { useState, useEffect, useMemo } from "react";
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
    Search,
    Loader2,
    Plus,
    Upload,
    Lightbulb,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@clerk/clerk-react";
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

const ALL_MONTHS_VALUE = "all";

function toMonthKey(value) {
    if (!value) return "";
    if (Array.isArray(value) && value.length >= 2) {
        return `${value[0]}-${String(value[1]).padStart(2, "0")}`;
    }
    const str = String(value);
    const match = str.match(/^(\d{4})[-,](\d{1,2})/);
    if (match) {
        return `${match[1]}-${match[2].padStart(2, "0")}`;
    }
    return str.slice(0, 7);
}

function toDisplayDate(value) {
    if (!value) return null;
    if (Array.isArray(value) && value.length >= 3) {
        return new Date(Number(value[0]), Number(value[1]) - 1, Number(value[2]));
    }
    return new Date(value);
}

function buildTransactionIdempotencyKey(payload) {
    const amount = Number(payload.amount || 0).toFixed(2);
    const date = payload.transactionDate || payload.date || "";
    const type = String(payload.type || "").toUpperCase();
    const description = String(payload.description || "").trim().toLowerCase();
    const vendor = String(payload.vendor || "").trim().toLowerCase();
    return `txn:${type}:${date}:${amount}:${description}:${vendor}`;
}

function getTransactionCategoryDisplay(txn) {
    const type = String(txn.type || "").toUpperCase();
    if (type === "INCOME") {
        return {
            label: "Payment Received",
            color: "#4CBB17",
        };
    }

    const normalizedCategory = String(txn.category || "").toLowerCase();
    const matched = CATEGORIES.find((category) => category.value === normalizedCategory);
    return matched || CATEGORIES[CATEGORIES.length - 1];
}

export default function TransactionsPage() {
    const { getToken } = useAuth();
    const { userId: internalUserId, orgId: internalOrgId } = useOnboardingStatus();
    
    const [transactions, setTransactions] = useState([]);
    const [invoices, setInvoices] = useState([]);
    const [orgName, setOrgName] = useState("MoneyOps Workspace");
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [filterCategory, setFilterCategory] = useState("all");
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [selectedMonth, setSelectedMonth] = useState(ALL_MONTHS_VALUE);
    const [aiInsight, setAiInsight] = useState(null);
    const [isSavingTransaction, setIsSavingTransaction] = useState(false);
    
    const [newTransaction, setNewTransaction] = useState({
        amount: "",
        type: "expense",
        category: "",
        description: "",
        vendor: "",
        vendorGstin: "",
        vendorPan: "",
        gstAmount: "",
        itcEligible: false,
        hasReceipt: false,
        date: new Date().toISOString().split("T")[0],
    });

    useEffect(() => {
        if (internalUserId && internalOrgId) {
            fetchTransactions();
        }
    }, [internalUserId, internalOrgId]);

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
            setTransactions(txns);

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
        const totalExpenses = visibleTransactions
            .filter((t) => String(t.type).toUpperCase() === "EXPENSE")
            .reduce((sum, t) => sum + Math.abs(Number(t.amount || 0)), 0);
        const totalIncome = visibleTransactions
            .filter((t) => String(t.type).toUpperCase() === "INCOME")
            .reduce((sum, t) => sum + Math.abs(Number(t.amount || 0)), 0);
        const scopedRevenue = invoices
            .filter((inv) => selectedMonth === ALL_MONTHS_VALUE || String(inv.issueDate || "").startsWith(selectedMonth))
            .reduce((sum, inv) => sum + Number(inv.totalAmount || 0), 0);
        const selectedMonthLabel = selectedMonth === ALL_MONTHS_VALUE
            ? "all recorded periods"
            : monthOptions.find((m) => m.value === selectedMonth)?.label || selectedMonth;

        if (!transactions.length && !invoices.length) {
            setAiInsight("No live transactions or invoices were found for this workspace yet. Record transactions or create invoices first, then this page can summarize actual performance.");
            return;
        }

        if (!visibleTransactions.length) {
            setAiInsight(`Invoices raised in ${selectedMonthLabel} total ₹${scopedRevenue.toLocaleString("en-IN")}, but there are no recorded transactions in that period. That means billing exists, while operating cash movements have not been captured here yet.`);
            return;
        }

        setAiInsight(`For ${selectedMonthLabel}, recorded expenses are ₹${totalExpenses.toLocaleString("en-IN")} and recorded income transactions are ₹${totalIncome.toLocaleString("en-IN")}. Invoices raised in the same period total ₹${scopedRevenue.toLocaleString("en-IN")}. Use invoices for billed revenue and this page for actual money movement.`);
    };

    useEffect(() => {
        fetchAiInsight();
    }, [transactions, invoices, selectedMonth]);

    const monthOptions = useMemo(() => {
        const keys = new Set();

        transactions.forEach((txn) => {
            const key = toMonthKey(txn.transactionDate || txn.date || txn.createdAt);
            if (key) keys.add(key);
        });

        invoices.forEach((invoice) => {
            const key = toMonthKey(invoice.issueDate);
            if (key) keys.add(key);
        });

        const derived = Array.from(keys)
            .filter(Boolean)
            .sort((a, b) => b.localeCompare(a))
            .map((value) => {
                const parsed = new Date(`${value}-01T00:00:00`);
                return {
                    value,
                    label: Number.isNaN(parsed.getTime())
                        ? value
                        : parsed.toLocaleDateString("en-IN", { month: "long", year: "numeric" }),
                };
            });

        return [{ value: ALL_MONTHS_VALUE, label: "All time" }, ...derived];
    }, [transactions, invoices]);

    const visibleTransactions = useMemo(() => (
        transactions.filter((txn) => (
            selectedMonth === ALL_MONTHS_VALUE
            || toMonthKey(txn.transactionDate || txn.date || txn.createdAt) === selectedMonth
        ))
    ), [transactions, selectedMonth]);

    const handleAddTransaction = async () => {
        if (!newTransaction.amount || !newTransaction.description) {
            toast.error("Please fill in amount and description");
            return;
        }
        if (isSavingTransaction) {
            return;
        }
        
        try {
            setIsSavingTransaction(true);
            const token = await getToken();
            const payload = {
                ...newTransaction,
                amount: parseFloat(newTransaction.amount),
                type: newTransaction.type === "income" ? "INCOME" : "EXPENSE",
                transactionDate: newTransaction.date,
                vendorName: newTransaction.vendor,
                vendorGstin: newTransaction.vendorGstin || null,
                vendorPan: newTransaction.vendorPan || null,
                gstAmount: newTransaction.gstAmount ? parseFloat(newTransaction.gstAmount) : null,
                itcEligible: newTransaction.type === "expense" ? Boolean(newTransaction.itcEligible) : false,
                hasReceipt: newTransaction.type === "expense" ? Boolean(newTransaction.hasReceipt) : false,
            };
            const res = await fetch("/api/transactions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId,
                },
                body: JSON.stringify({
                    ...payload,
                    idempotencyKey: buildTransactionIdempotencyKey(payload),
                }),
            });
            
            if (res.ok) {
                toast.success("Transaction added successfully");
            } else {
                throw new Error("Failed to add transaction");
            }
            
            setIsAddOpen(false);
            setNewTransaction({
                amount: "",
                type: "expense",
                category: "",
                description: "",
                vendor: "",
                vendorGstin: "",
                vendorPan: "",
                gstAmount: "",
                itcEligible: false,
                hasReceipt: false,
                date: new Date().toISOString().split("T")[0],
            });
            fetchTransactions();
        } catch {
            toast.error("Could not save transaction");
        } finally {
            setIsSavingTransaction(false);
        }
    };

    const stats = {
        totalExpenses: visibleTransactions
            .filter((t) => String(t.type).toUpperCase() === "EXPENSE")
            .reduce((sum, t) => sum + Math.abs(Number(t.amount || 0)), 0),
        totalIncome: visibleTransactions
            .filter((t) => String(t.type).toUpperCase() === "INCOME")
            .reduce((sum, t) => sum + Math.abs(Number(t.amount || 0)), 0),
        grossRevenue: invoices
            .filter((inv) => selectedMonth === ALL_MONTHS_VALUE || String(inv.issueDate || "").startsWith(selectedMonth))
            .reduce((sum, inv) => sum + Number(inv.totalAmount || 0), 0),
        uncategorized: visibleTransactions.filter((t) => (
            String(t.type).toUpperCase() === "EXPENSE"
            && (String(t.category || "").toLowerCase() === "uncategorized" || !t.category)
        )).length,
    };
    const netMargin = stats.grossRevenue > 0
        ? (((stats.grossRevenue - stats.totalExpenses) / stats.grossRevenue) * 100)
        : 0;

    const categoryBreakdown = CATEGORIES.map(cat => {
        const catTransactions = visibleTransactions.filter(
            (t) => t.category === cat.value && String(t.type).toUpperCase() === "EXPENSE"
        );
        const total = catTransactions.reduce((sum, t) => sum + Math.abs(Number(t.amount || 0)), 0);
        return { ...cat, total, count: catTransactions.length };
    }).filter(c => c.total > 0).sort((a, b) => b.total - a.total);

    const filteredTransactions = visibleTransactions.filter(txn => {
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
                    <p className="mo-text-secondary mt-1">{orgName} · {monthOptions.find(m => m.value === selectedMonth)?.label || "All time"}</p>
                </div>
                
                <div className="flex items-center gap-3 flex-wrap">
                    <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                        <SelectTrigger className="bg-[#1A1A1A] border-[#2A2A2A] text-white w-[160px]">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                            {monthOptions.map(m => (
                                <SelectItem key={m.value} value={m.value} className="text-white">{m.label}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                        <DialogTrigger asChild>
                            <button className="mo-btn-primary flex items-center gap-2">
                                <Plus className="h-4 w-4" /> Add Transaction
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
                                {newTransaction.type === "expense" && (
                                    <>
                                        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                                            <div className="grid gap-2">
                                                <label className="text-sm font-medium text-[#A0A0A0]">Vendor GSTIN</label>
                                                <input
                                                    placeholder="27ABCDE1234F1Z5"
                                                    value={newTransaction.vendorGstin}
                                                    onChange={(e) => setNewTransaction(p => ({ ...p, vendorGstin: e.target.value.toUpperCase() }))}
                                                    style={inputStyle}
                                                    maxLength={15}
                                                />
                                            </div>
                                            <div className="grid gap-2">
                                                <label className="text-sm font-medium text-[#A0A0A0]">Vendor PAN</label>
                                                <input
                                                    placeholder="ABCDE1234F"
                                                    value={newTransaction.vendorPan}
                                                    onChange={(e) => setNewTransaction(p => ({ ...p, vendorPan: e.target.value.toUpperCase() }))}
                                                    style={inputStyle}
                                                    maxLength={10}
                                                />
                                            </div>
                                        </div>
                                        <div className="grid gap-2">
                                            <label className="text-sm font-medium text-[#A0A0A0]">GST Amount</label>
                                            <input
                                                type="number"
                                                placeholder="Leave blank to auto-derive where possible"
                                                value={newTransaction.gstAmount}
                                                onChange={(e) => setNewTransaction(p => ({ ...p, gstAmount: e.target.value }))}
                                                style={inputStyle}
                                            />
                                        </div>
                                        <div className="grid gap-3 rounded-lg border border-[#2A2A2A] bg-[#161616] p-3">
                                            <label className="flex items-center justify-between gap-3 text-sm text-white">
                                                <span>Eligible for ITC</span>
                                                <input
                                                    type="checkbox"
                                                    checked={newTransaction.itcEligible}
                                                    onChange={(e) => setNewTransaction(p => ({ ...p, itcEligible: e.target.checked }))}
                                                />
                                            </label>
                                            <label className="flex items-center justify-between gap-3 text-sm text-white">
                                                <span>Receipt or tax invoice available</span>
                                                <input
                                                    type="checkbox"
                                                    checked={newTransaction.hasReceipt}
                                                    onChange={(e) => setNewTransaction(p => ({ ...p, hasReceipt: e.target.checked }))}
                                                />
                                            </label>
                                        </div>
                                    </>
                                )}
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Date</label>
                                    <input
                                        type="date"
                                        value={newTransaction.date}
                                        onChange={(e) => setNewTransaction(p => ({ ...p, date: e.target.value }))}
                                        style={{ ...inputStyle, colorScheme: "dark" }}
                                    />
                                </div>
                                <button
                                    onClick={handleAddTransaction}
                                    className="mo-btn-primary w-full disabled:opacity-50"
                                    disabled={isSavingTransaction}
                                >
                                    {isSavingTransaction ? "Saving..." : "Save Transaction"}
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
                                {monthOptions.map(m => (
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
                    <h3 className="font-semibold text-white">All transactions — {monthOptions.find(m => m.value === selectedMonth)?.label || "All time"}</h3>
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
                        <Select value={selectedMonth} onValueChange={setSelectedMonth}>
                            <SelectTrigger className="bg-[#1A1A1A] border-[#2A2A2A] text-white w-[160px]">
                                <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                {monthOptions.map(m => (
                                    <SelectItem key={m.value} value={m.value} className="text-white">{m.label}</SelectItem>
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
                        <table className="w-full min-w-[980px] table-fixed text-sm">
                            <thead>
                                <tr className="border-b border-[#2A2A2A]">
                                    <th className="w-[100px] text-left py-3 px-4 text-[#666] font-medium">Date</th>
                                    <th className="w-[42%] text-left py-3 px-4 text-[#666] font-medium">Description</th>
                                    <th className="w-[160px] text-left py-3 px-4 text-[#666] font-medium">Category</th>
                                    <th className="w-[240px] text-left py-3 px-4 text-[#666] font-medium">Vendor</th>
                                    <th className="w-[130px] text-right py-3 px-4 text-[#666] font-medium">Amount</th>
                                    <th className="w-[90px] text-left py-3 px-4 text-[#666] font-medium">Type</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredTransactions.map(txn => {
                                    const categoryDisplay = getTransactionCategoryDisplay(txn);
                                    const displayDate = toDisplayDate(txn.transactionDate || txn.date || txn.createdAt);
                                    return (
                                        <tr key={txn.id} className="border-b border-[#1A1A1A] hover:bg-[#111111] transition-colors">
                                            <td className="py-3 px-4 text-[#CCC]">
                                                {displayDate && !Number.isNaN(displayDate.getTime())
                                                    ? displayDate.toLocaleDateString("en-IN", { day: "2-digit", month: "short" })
                                                    : "—"}
                                            </td>
                                            <td className="py-3 px-4 text-white font-medium break-words">{txn.description || "Recorded transaction"}</td>
                                            <td className="py-3 px-4">
                                                <span
                                                    className="inline-flex max-w-full whitespace-nowrap rounded px-2 py-1 text-xs font-medium"
                                                    style={{ backgroundColor: `${categoryDisplay.color}20`, color: categoryDisplay.color }}
                                                    title={categoryDisplay.label}
                                                >
                                                    {categoryDisplay.label}
                                                </span>
                                            </td>
                                            <td className="py-3 px-4 text-[#CCC] truncate" title={txn.vendor || txn.vendorName || txn.clientName || txn.referenceNumber || "—"}>{txn.vendor || txn.vendorName || txn.clientName || txn.referenceNumber || "—"}</td>
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
                                No transactions found for this filter
                            </div>
                        )}
                    </div>
                )}
            </div>

        </div>
    );
}
