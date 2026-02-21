import { useState, useEffect } from "react";
import { useAuth } from "@clerk/clerk-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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

// ── Constants ─────────────────────────────────────────────────────────────────

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
    const { getToken } = useAuth();
    const [transactions, setTransactions] = useState([]);
    const [accounts, setAccounts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [filterType, setFilterType] = useState("all");

    // Add Transaction dialog state
    const [isAddOpen, setIsAddOpen] = useState(false);
    const [newTransaction, setNewTransaction] = useState(BLANK_TRANSACTION);

    // Upload CSV dialog state
    const [isUploadOpen, setIsUploadOpen] = useState(false);
    const [uploadFile, setUploadFile] = useState(null);
    const [uploadAccountId, setUploadAccountId] = useState("");
    const [isUploading, setIsUploading] = useState(false);

    useEffect(() => {
        fetchTransactions();
        fetchAccounts();
    }, []);

    // ── API ───────────────────────────────────────────────────────────────────

    const fetchTransactions = async () => {
        try {
            setLoading(true);
            const token = await getToken();
            const res = await fetch("/api/transactions", {
                headers: { Authorization: `Bearer ${token}` }
            });
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
            const token = await getToken();
            const res = await fetch("/api/accounts", {
                headers: { Authorization: `Bearer ${token}` }
            });
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
            const token = await getToken();
            const res = await fetch("/api/transactions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({
                    ...newTransaction,
                    amount: parseFloat(newTransaction.amount),
                }),
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

            const token = await getToken();
            const res = await fetch("/api/transactions/import", {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
                body: formData,
            });

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
            const token = await getToken();
            const res = await fetch(`/api/transactions?id=${id}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) throw new Error("Failed to delete transaction");

            toast.success("Transaction deleted successfully");
            fetchTransactions();
        } catch {
            toast.error("Failed to delete transaction");
        }
    };

    // ── Derived state ─────────────────────────────────────────────────────────

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
        income: transactions
            .filter((t) => t.type === "credit")
            .reduce((sum, t) => sum + Math.abs(t.amount), 0),
        expenses: transactions
            .filter((t) => t.type === "debit")
            .reduce((sum, t) => sum + Math.abs(t.amount), 0),
    };

    // ── Render ────────────────────────────────────────────────────────────────

    return (
        <div className="space-y-6">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Transactions</h2>
                    <p className="text-slate-500 text-sm mt-1">
                        View and manage your transactions
                    </p>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                    {/* Add Transaction */}
                    <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
                        <DialogTrigger asChild>
                            <Button>
                                <Plus className="h-4 w-4 mr-2" /> Add Transaction
                            </Button>
                        </DialogTrigger>
                        <DialogContent className="max-h-[90vh] overflow-y-auto">
                            <DialogHeader>
                                <DialogTitle>Add New Transaction</DialogTitle>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                {/* Account */}
                                <div className="grid gap-2">
                                    <Label>Account *</Label>
                                    <Select
                                        value={newTransaction.accountId}
                                        onValueChange={(val) =>
                                            setNewTransaction((p) => ({ ...p, accountId: val }))
                                        }
                                    >
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select account" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {accounts.map((acc) => (
                                                <SelectItem key={acc.id} value={acc.id}>
                                                    {acc.accountName} (₹{acc.balance?.toLocaleString("en-IN")})
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                {/* Amount + Type */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="grid gap-2">
                                        <Label>Amount *</Label>
                                        <Input
                                            id="txn-amount"
                                            type="number"
                                            placeholder="0.00"
                                            value={newTransaction.amount}
                                            onChange={(e) =>
                                                setNewTransaction((p) => ({ ...p, amount: e.target.value }))
                                            }
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <Label>Type</Label>
                                        <Select
                                            value={newTransaction.type}
                                            onValueChange={(val) =>
                                                setNewTransaction((p) => ({ ...p, type: val }))
                                            }
                                        >
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="debit">Expense (Debit)</SelectItem>
                                                <SelectItem value="credit">Income (Credit)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>

                                {/* Description */}
                                <div className="grid gap-2">
                                    <Label>Description *</Label>
                                    <Input
                                        id="txn-description"
                                        placeholder="Transaction description"
                                        value={newTransaction.description}
                                        onChange={(e) =>
                                            setNewTransaction((p) => ({ ...p, description: e.target.value }))
                                        }
                                    />
                                </div>

                                {/* Category */}
                                <div className="grid gap-2">
                                    <Label>Category</Label>
                                    <Input
                                        id="txn-category"
                                        placeholder="e.g., Food, Travel, Salary"
                                        value={newTransaction.category}
                                        onChange={(e) =>
                                            setNewTransaction((p) => ({ ...p, category: e.target.value }))
                                        }
                                    />
                                </div>

                                {/* Date */}
                                <div className="grid gap-2">
                                    <Label>Date</Label>
                                    <Input
                                        id="txn-date"
                                        type="date"
                                        value={newTransaction.date}
                                        onChange={(e) =>
                                            setNewTransaction((p) => ({ ...p, date: e.target.value }))
                                        }
                                    />
                                </div>

                                <Button onClick={handleAddTransaction}>Save Transaction</Button>
                            </div>
                        </DialogContent>
                    </Dialog>

                    {/* Upload CSV */}
                    <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
                        <DialogTrigger asChild>
                            <Button variant="outline">
                                <Upload className="h-4 w-4 mr-2" /> Upload CSV
                            </Button>
                        </DialogTrigger>
                        <DialogContent>
                            <DialogHeader>
                                <DialogTitle>Upload Transactions</DialogTitle>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                <div className="grid gap-2">
                                    <Label>Account</Label>
                                    <Select value={uploadAccountId} onValueChange={setUploadAccountId}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select account to import to" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {accounts.map((acc) => (
                                                <SelectItem key={acc.id} value={acc.id}>
                                                    {acc.accountName}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="grid gap-2">
                                    <Label>CSV File</Label>
                                    <Input
                                        id="txn-upload-file"
                                        type="file"
                                        accept=".csv"
                                        onChange={(e) =>
                                            setUploadFile(e.target.files ? e.target.files[0] : null)
                                        }
                                    />
                                </div>
                                <Button onClick={handleUploadTransactions} disabled={isUploading}>
                                    {isUploading ? (
                                        <>
                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Uploading…
                                        </>
                                    ) : (
                                        "Upload"
                                    )}
                                </Button>
                            </div>
                        </DialogContent>
                    </Dialog>

                    <Button variant="outline" size="sm" disabled>
                        <Filter className="h-4 w-4 mr-2" /> Filter
                    </Button>
                    <Button variant="outline" size="sm" disabled>
                        <Download className="h-4 w-4 mr-2" /> Export
                    </Button>
                </div>
            </div>

            {/* ── Stats Cards ───────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-3">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-slate-500">
                            Total Transactions
                        </CardTitle>
                        <CreditCard className="h-4 w-4 text-slate-400" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{stats.total}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-slate-500">
                            Total Income
                        </CardTitle>
                        <TrendingUp className="h-4 w-4 text-slate-400" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-green-600">
                            ₹{stats.income.toLocaleString("en-IN")}
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-sm font-medium text-slate-500">
                            Total Expenses
                        </CardTitle>
                        <TrendingDown className="h-4 w-4 text-slate-400" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-red-600">
                            ₹{stats.expenses.toLocaleString("en-IN")}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* ── Search + Type Filters ─────────────────────────────────────── */}
            <div className="flex items-center gap-4 flex-wrap">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input
                        placeholder="Search transactions…"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                    />
                </div>

                <div className="flex items-center gap-2">
                    {FILTER_TYPES.map((type) => (
                        <Button
                            key={type}
                            variant={filterType === type ? "default" : "outline"}
                            size="sm"
                            onClick={() => setFilterType(type)}
                            className={filterType === type ? "bg-green-600 hover:bg-green-700" : ""}
                        >
                            {FILTER_LABELS[type]}
                        </Button>
                    ))}
                </div>
            </div>

            {/* ── Transaction List ──────────────────────────────────────────── */}
            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
                </div>
            ) : filteredTransactions.length === 0 ? (
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-16">
                        <CreditCard className="h-16 w-16 text-slate-300 mb-4" />
                        <h3 className="text-lg font-semibold mb-2">
                            {searchQuery || filterType !== "all"
                                ? "No transactions found"
                                : "No transactions yet"}
                        </h3>
                        <p className="text-slate-400 text-sm text-center max-w-sm">
                            {searchQuery || filterType !== "all"
                                ? "Try adjusting your search or filters"
                                : "Add a transaction or upload a CSV to get started"}
                        </p>
                        <div className="mt-6 flex gap-2">
                            <Button onClick={() => setIsAddOpen(true)}>
                                <Plus className="h-4 w-4 mr-2" /> Add Transaction
                            </Button>
                            <Button variant="outline" onClick={() => setIsUploadOpen(true)}>
                                <Upload className="h-4 w-4 mr-2" /> Upload CSV
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            ) : (
                <Card>
                    <CardContent className="p-0">
                        <div className="divide-y">
                            {filteredTransactions.map((transaction) => (
                                <div
                                    key={transaction.id}
                                    className="flex items-center justify-between p-4 hover:bg-slate-50 transition-colors group"
                                >
                                    {/* Left: icon + details */}
                                    <div className="flex items-center gap-4 flex-1 min-w-0">
                                        <div
                                            className={`p-2 rounded-full shrink-0 ${transaction.type === "credit"
                                                ? "bg-green-100 text-green-600"
                                                : "bg-red-100 text-red-600"
                                                }`}
                                        >
                                            {transaction.type === "credit" ? (
                                                <TrendingUp className="h-4 w-4" />
                                            ) : (
                                                <TrendingDown className="h-4 w-4" />
                                            )}
                                        </div>

                                        <div className="flex-1 min-w-0">
                                            <p className="font-medium truncate">
                                                {transaction.description ||
                                                    transaction.merchantName ||
                                                    "Transaction"}
                                            </p>
                                            <div className="flex items-center gap-2 text-sm text-slate-400 flex-wrap">
                                                <span>{new Date(transaction.date).toLocaleDateString()}</span>
                                                {transaction.category && (
                                                    <>
                                                        <span>•</span>
                                                        <Badge variant="outline" className="text-xs">
                                                            {transaction.category}
                                                        </Badge>
                                                    </>
                                                )}
                                                {transaction.account && (
                                                    <>
                                                        <span>•</span>
                                                        <span className="text-xs">
                                                            {transaction.account.accountName}
                                                        </span>
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Right: amount + status + delete */}
                                    <div className="flex items-center gap-4 shrink-0">
                                        <div className="text-right">
                                            <p
                                                className={`font-semibold ${transaction.type === "credit"
                                                    ? "text-green-600"
                                                    : "text-red-600"
                                                    }`}
                                            >
                                                {transaction.type === "credit" ? "+" : "−"}₹
                                                {Math.abs(transaction.amount).toLocaleString("en-IN")}
                                            </p>
                                            {transaction.status && (
                                                <Badge
                                                    variant={
                                                        transaction.status === "completed"
                                                            ? "default"
                                                            : "secondary"
                                                    }
                                                    className="text-xs mt-1"
                                                >
                                                    {transaction.status}
                                                </Badge>
                                            )}
                                        </div>

                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-700 hover:bg-red-50"
                                            onClick={() => handleDeleteTransaction(transaction.id)}
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
