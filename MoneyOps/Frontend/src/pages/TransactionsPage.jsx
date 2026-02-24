import { useState, useEffect } from "react";
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
} from "lucide-react";
import { toast } from "sonner";

const BLANK_TRANSACTION = {
    accountId: "",
    amount: "",
    type: "debit",
    category: "",
    description: "",
    date: new Date().toISOString().split("T")[0],
};

const FILTER_TYPES = ["all", "credit", "debit"];
const FILTER_LABELS = { all: "All", credit: "Income", debit: "Expenses" };

export default function TransactionsPage() {
    const [transactions, setTransactions] = useState([]);
    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [filterType, setFilterType] = useState("all");
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [newTransaction, setNewTransaction] = useState(BLANK_TRANSACTION);
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [uploadFile, setUploadFile] = useState(null);
    const [uploadAccountId, setUploadAccountId] = useState("");
    const [isUploading, setIsUploading] = useState(false);

    useEffect(() => {
        fetchTransactions();
        fetchAccounts();
    }, []);

    const fetchTransactions = async () => {
        try {
            setLoading(true);
            const res = await fetch("/api/transactions");
            if (!res.ok) throw new Error("Failed to fetch");
            const data = await res.json();
            setTransactions(Array.isArray(data) ? data : data.transactions || []);
        } catch {
            toast.error("Failed to load transactions");
            setTransactions([]);
        } finally {
            setLoading(false);
        }
    };

    const fetchAccounts = async () => {
        try {
            const res = await fetch("/api/accounts");
            if (res.ok) {
                const data = await res.json();
                setAccounts(data.accounts || []);
            }
        } catch (error) {
            console.error("Failed to fetch accounts", error);
        }
    };

    const handleAddTransaction = async () => {
        if (!newTransaction.accountId || !newTransaction.amount || !newTransaction.description) {
            toast.error("Please fill in all required fields");
            return;
        }
        try {
            const res = await fetch("/api/transactions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ ...newTransaction, amount: parseFloat(newTransaction.amount) }),
            });
            if (!res.ok) throw new Error("Failed to create transaction");
            toast.success("Transaction added successfully");
            setIsAddOpen(false);
            setNewTransaction(BLANK_TRANSACTION);
            fetchTransactions();
        } catch {
            toast.error("Failed to add transaction");
        }
    };

    const handleUploadTransactions = async () => {
        if (!uploadFile || !uploadAccountId) {
            toast.error("Please select a file and an account");
            return;
        }
        try {
            setIsUploading(true);
            const formData = new FormData();
            formData.append("file", uploadFile);
            formData.append("accountId", uploadAccountId);
            const res = await fetch("/api/transactions/import", { method: "POST", body: formData });
            if (!res.ok) throw new Error("Upload failed");
            const data = await res.json();
            toast.success(data.message || "Transactions uploaded successfully");
            setIsUploadOpen(false);
            setUploadFile(null);
            setUploadAccountId("");
            fetchTransactions();
        } catch {
            toast.error("Failed to upload transactions");
        } finally {
            setIsUploading(false);
        }
    };

    const handleDeleteTransaction = async (id) => {
        if (!window.confirm("Delete this transaction? This cannot be undone.")) return;
        try {
            const res = await fetch(`/api/transactions?id=${id}`, { method: "DELETE" });
            if (!res.ok) throw new Error("Failed to delete transaction");
            toast.success("Transaction deleted successfully");
            fetchTransactions();
        } catch {
            toast.error("Failed to delete transaction");
        }
    };

    const filteredTransactions = transactions.filter((txn) => {
        const matchesSearch =
            !searchQuery ||
            txn.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            txn.merchantName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            txn.category?.toLowerCase().includes(searchQuery.toLowerCase());
        const matchesType = filterType === "all" || txn.type === filterType;
        return matchesSearch && matchesType;
    });

    const stats = {
        total: transactions.length,
        income: transactions.filter((t) => t.type === "credit").reduce((sum, t) => sum + Math.abs(t.amount), 0),
        expenses: transactions.filter((t) => t.type === "debit").reduce((sum, t) => sum + Math.abs(t.amount), 0),
    };

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

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Transactions</h1>
                    <p className="mo-text-secondary mt-1">View and manage your transactions</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                    {/* Add Transaction */}
                    <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                        <DialogTrigger asChild>
                            <button className="mo-btn-primary flex items-center gap-2">
                                <Plus className="h-4 w-4" /> Add Transaction
                            </button>
                        </DialogTrigger>
                        <DialogContent className="max-h-[90vh] overflow-y-auto bg-[#111111] border-[#2A2A2A] text-white">
                            <DialogHeader>
                                <DialogTitle className="text-white">Add New Transaction</DialogTitle>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Account *</label>
                                    <Select
                                        value={newTransaction.accountId}
                                        onValueChange={(val) => setNewTransaction((p) => ({ ...p, accountId: val }))}
                                    >
                                        <SelectTrigger className="bg-[#1A1A1A] border-[#2A2A2A] text-white">
                                            <SelectValue placeholder="Select account" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                            {accounts.map((acc) => (
                                                <SelectItem key={acc.id} value={acc.id} className="text-white hover:bg-[#2A2A2A]">
                                                    {acc.accountName} (₹{acc.balance?.toLocaleString("en-IN")})
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium text-[#A0A0A0]">Amount *</label>
                                        <input
                                            id="txn-amount"
                                            type="number"
                                            placeholder="0.00"
                                            value={newTransaction.amount}
                                            onChange={(e) => setNewTransaction((p) => ({ ...p, amount: e.target.value }))}
                                            style={inputStyle}
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium text-[#A0A0A0]">Type</label>
                                        <Select
                                            value={newTransaction.type}
                                            onValueChange={(val) => setNewTransaction((p) => ({ ...p, type: val }))}
                                        >
                                            <SelectTrigger className="bg-[#1A1A1A] border-[#2A2A2A] text-white">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                                <SelectItem value="debit" className="text-white hover:bg-[#2A2A2A]">Expense (Debit)</SelectItem>
                                                <SelectItem value="credit" className="text-white hover:bg-[#2A2A2A]">Income (Credit)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Description *</label>
                                    <input
                                        id="txn-description"
                                        placeholder="Transaction description"
                                        value={newTransaction.description}
                                        onChange={(e) => setNewTransaction((p) => ({ ...p, description: e.target.value }))}
                                        style={inputStyle}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Category</label>
                                    <input
                                        id="txn-category"
                                        placeholder="e.g., Food, Travel, Salary"
                                        value={newTransaction.category}
                                        onChange={(e) => setNewTransaction((p) => ({ ...p, category: e.target.value }))}
                                        style={inputStyle}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Date</label>
                                    <input
                                        id="txn-date"
                                        type="date"
                                        value={newTransaction.date}
                                        onChange={(e) => setNewTransaction((p) => ({ ...p, date: e.target.value }))}
                                        style={{ ...inputStyle, colorScheme: "dark" }}
                                    />
                                </div>
                                <button onClick={handleAddTransaction} className="mo-btn-primary w-full">
                                    Save Transaction
                                </button>
                            </div>
                        </DialogContent>
                    </Dialog>

                    {/* Upload CSV */}
                    <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
                        <DialogTrigger asChild>
                            <button className="mo-btn-secondary flex items-center gap-2">
                                <Upload className="h-4 w-4" /> Upload CSV
                            </button>
                        </DialogTrigger>
                        <DialogContent className="bg-[#111111] border-[#2A2A2A] text-white">
                            <DialogHeader>
                                <DialogTitle className="text-white">Upload Transactions</DialogTitle>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Account</label>
                                    <Select value={uploadAccountId} onValueChange={setUploadAccountId}>
                                        <SelectTrigger className="bg-[#1A1A1A] border-[#2A2A2A] text-white">
                                            <SelectValue placeholder="Select account to import to" />
                                        </SelectTrigger>
                                        <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                            {accounts.map((acc) => (
                                                <SelectItem key={acc.id} value={acc.id} className="text-white hover:bg-[#2A2A2A]">
                                                    {acc.accountName}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">CSV File</label>
                                    <input
                                        id="txn-upload-file"
                                        type="file"
                                        accept=".csv"
                                        onChange={(e) => setUploadFile(e.target.files ? e.target.files[0] : null)}
                                        className="text-sm text-[#A0A0A0] file:mr-3 file:px-3 file:py-1.5 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-[#4CBB17] file:text-black"
                                        style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A", borderRadius: "8px", padding: "8px 12px" }}
                                    />
                                </div>
                                <button
                                    onClick={handleUploadTransactions}
                                    disabled={isUploading}
                                    className="mo-btn-primary w-full flex items-center justify-center gap-2"
                                >
                                    {isUploading ? (
                                        <><Loader2 className="h-4 w-4 animate-spin" /> Uploading…</>
                                    ) : (
                                        "Upload"
                                    )}
                                </button>
                            </div>
                        </DialogContent>
                    </Dialog>

                    <button className="mo-btn-secondary flex items-center gap-2 opacity-50 cursor-not-allowed" disabled>
                        <Filter className="h-4 w-4" /> Filter
                    </button>
                    <button className="mo-btn-secondary flex items-center gap-2 opacity-50 cursor-not-allowed" disabled>
                        <Download className="h-4 w-4" /> Export
                    </button>
                </div>
            </div>

            {/* ── Stats ───────────────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-3">
                <div className="mo-stat-card">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-[#A0A0A0]">Total Transactions</p>
                        <CreditCard className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-3xl font-bold text-white">{stats.total}</div>
                </div>
                <div className="mo-stat-card">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-[#A0A0A0]">Total Income</p>
                        <TrendingUp className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-3xl font-bold text-[#4CBB17]">
                        ₹{stats.income.toLocaleString("en-IN")}
                    </div>
                </div>
                <div className="mo-stat-card">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-[#A0A0A0]">Total Expenses</p>
                        <TrendingDown className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-3xl font-bold text-[#CD1C18]">
                        ₹{stats.expenses.toLocaleString("en-IN")}
                    </div>
                </div>
            </div>

            {/* ── Search + Filter ──────────────────────────────────────────────── */}
            <div className="flex items-center gap-4 flex-wrap">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#A0A0A0]" />
                    <input
                        placeholder="Search transactions…"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2.5 rounded-lg text-sm text-white placeholder-[#A0A0A0] focus:outline-none"
                        style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A", borderRadius: "8px" }}
                    />
                </div>
                <div className="flex items-center gap-2">
                    {FILTER_TYPES.map((type) => (
                        <button
                            key={type}
                            onClick={() => setFilterType(type)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${filterType === type
                                    ? "bg-[#4CBB17] text-black"
                                    : "bg-[#1A1A1A] text-[#A0A0A0] border border-[#2A2A2A] hover:border-[#4CBB17] hover:text-white"
                                }`}
                        >
                            {FILTER_LABELS[type]}
                        </button>
                    ))}
                </div>
            </div>

            {/* ── Transaction List ─────────────────────────────────────────────── */}
            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
                </div>
            ) : filteredTransactions.length === 0 ? (
                <div className="mo-card flex flex-col items-center justify-center py-16 border-dashed">
                    <CreditCard className="h-16 w-16 text-[#2A2A2A] mb-4" />
                    <h3 className="text-lg font-semibold text-white mb-2">
                        {searchQuery || filterType !== "all"
                            ? "No transactions found"
                            : "No transactions yet"}
                    </h3>
                    <p className="text-[#A0A0A0] text-sm text-center max-w-sm">
                        {searchQuery || filterType !== "all"
                            ? "Try adjusting your search or filters"
                            : "Add a transaction or upload a CSV to get started"}
                    </p>
                    <div className="mt-6 flex gap-2">
                        <button onClick={() => setIsAddOpen(true)} className="mo-btn-primary flex items-center gap-2">
                            <Plus className="h-4 w-4" /> Add Transaction
                        </button>
                        <button onClick={() => setIsUploadOpen(true)} className="mo-btn-secondary flex items-center gap-2">
                            <Upload className="h-4 w-4" /> Upload CSV
                        </button>
                    </div>
                </div>
            ) : (
                <div className="mo-card !p-0 overflow-hidden">
                    <div className="divide-y divide-[#2A2A2A]">
                        {filteredTransactions.map((transaction) => (
                            <div
                                key={transaction.id}
                                className="flex items-center justify-between p-4 hover:bg-[#111111] transition-colors group"
                            >
                                {/* Left: icon + details */}
                                <div className="flex items-center gap-4 flex-1 min-w-0">
                                    <div
                                        className={`p-2 rounded-full shrink-0 ${transaction.type === "credit"
                                                ? "bg-[#4CBB1720] text-[#4CBB17]"
                                                : "bg-[#CD1C1820] text-[#CD1C18]"
                                            }`}
                                    >
                                        {transaction.type === "credit" ? (
                                            <TrendingUp className="h-4 w-4" />
                                        ) : (
                                            <TrendingDown className="h-4 w-4" />
                                        )}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="font-medium text-white truncate">
                                            {transaction.description || transaction.merchantName || "Transaction"}
                                        </p>
                                        <div className="flex items-center gap-2 text-sm text-[#A0A0A0] flex-wrap mt-0.5">
                                            <span>{new Date(transaction.date).toLocaleDateString()}</span>
                                            {transaction.category && (
                                                <>
                                                    <span>•</span>
                                                    <span className="text-xs px-1.5 py-0.5 rounded bg-[#2A2A2A] text-[#A0A0A0]">
                                                        {transaction.category}
                                                    </span>
                                                </>
                                            )}
                                            {transaction.account && (
                                                <>
                                                    <span>•</span>
                                                    <span className="text-xs">{transaction.account.accountName}</span>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Right: amount + delete */}
                                <div className="flex items-center gap-4 shrink-0">
                                    <div className="text-right">
                                        <p
                                            className={`font-semibold ${transaction.type === "credit" ? "text-[#4CBB17]" : "text-[#CD1C18]"
                                                }`}
                                        >
                                            {transaction.type === "credit" ? "+" : "−"}₹
                                            {Math.abs(transaction.amount).toLocaleString("en-IN")}
                                        </p>
                                        {transaction.status && (
                                            <span
                                                className={`text-xs px-1.5 py-0.5 rounded mt-1 inline-block ${transaction.status === "completed"
                                                        ? "bg-[#4CBB1720] text-[#4CBB17]"
                                                        : "bg-[#A0A0A020] text-[#A0A0A0]"
                                                    }`}
                                            >
                                                {transaction.status}
                                            </span>
                                        )}
                                    </div>
                                    <button
                                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-[#CD1C1820] text-[#A0A0A0] hover:text-[#CD1C18]"
                                        onClick={() => handleDeleteTransaction(transaction.id)}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
