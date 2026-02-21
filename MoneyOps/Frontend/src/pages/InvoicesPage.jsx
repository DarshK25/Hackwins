import { useState, useEffect } from "react";
import { useAuth } from "@clerk/clerk-react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
    Plus,
    IndianRupee,
    Loader2,
    RefreshCw,
    Eye,
    Send,
    Download,
    MoreVertical,
    Search,
} from "lucide-react";
import { toast } from "sonner";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// ── Status badge styles ───────────────────────────────────────────────────────

const STATUS_CLASSES = {
    paid: "bg-green-500/10 text-green-600 hover:bg-green-500/20",
    sent: "bg-blue-500/10 text-blue-600 hover:bg-blue-500/20",
    overdue: "bg-red-500/10 text-red-600 hover:bg-red-500/20",
    draft: "bg-slate-500/10 text-slate-500 hover:bg-slate-500/20",
};

const getStatusClass = (status) =>
    STATUS_CLASSES[status] ?? STATUS_CLASSES.draft;

// ── Filter tab config ─────────────────────────────────────────────────────────

const TABS = ["all", "draft", "sent", "paid", "overdue"];

export default function InvoicesPage() {
    const { getToken } = useAuth();
    const navigate = useNavigate();
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState("all");
    const [searchQuery, setSearchQuery] = useState("");
    const [actionLoading, setActionLoading] = useState(null);

    useEffect(() => {
        fetchInvoices();
    }, []);

    // ── API ───────────────────────────────────────────────────────────────────

    const fetchInvoices = async () => {
        try {
            setLoading(true);
            const token = await getToken();
            const res = await fetch("/api/invoices", {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) throw new Error("Failed to fetch");
            const data = await res.json();
            setInvoices(data.invoices || []);
        } catch {
            toast.error("Failed to load invoices");
            setInvoices([]);
        } finally {
            setLoading(false);
        }
    };

    const handleViewInvoice = (invoice) => {
        navigate(`/invoices/${invoice.id}`);
    };

    const handleSendInvoice = async (invoice) => {
        if (!invoice.client?.email && !invoice.description?.includes("@")) {
            toast.error("No email address found for this client");
            return;
        }

        setActionLoading(invoice.id);
        try {
            const token = await getToken();
            const res = await fetch(`/api/invoices/${invoice.id}/send`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` }
            });
            const data = await res.json();
            if (!res.ok || !data.success) throw new Error(data.message || "Failed to send");

            toast.success(`Invoice sent to ${invoice.client?.email || "client"}`);
            fetchInvoices();
        } catch (error) {
            toast.error(error?.message || "Failed to send invoice");
        } finally {
            setActionLoading(null);
        }
    };

    const handleDownloadInvoice = async (invoice) => {
        setActionLoading(invoice.id);
        try {
            toast.info("Generating PDF…");
            const token = await getToken();
            const res = await fetch(`/api/invoices/${invoice.id}/download`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) throw new Error("Failed to generate PDF");

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `invoice-${invoice.invoiceNumber}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            toast.success("Invoice downloaded successfully");
        } catch (error) {
            toast.error(error?.message || "Failed to download invoice");
        } finally {
            setActionLoading(null);
        }
    };

    // ── Derived state ─────────────────────────────────────────────────────────

    const stats = {
        total: invoices.length,
        paid: invoices.filter((inv) => inv.status === "paid").length,
        pending: invoices.filter((inv) => inv.status === "sent" || inv.status === "draft").length,
        overdue: invoices.filter((inv) => inv.status === "overdue").length,
        paidAmount: invoices
            .filter((inv) => inv.status === "paid")
            .reduce((sum, inv) => sum + (inv.total || 0), 0),
    };

    const filteredInvoices = invoices.filter((invoice) => {
        const statusMatch =
            activeTab === "all" || invoice.status === activeTab;

        const searchMatch =
            !searchQuery ||
            invoice.invoiceNumber?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            invoice.client?.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            invoice.description?.toLowerCase().includes(searchQuery.toLowerCase());

        return statusMatch && searchMatch;
    });

    // ── Render ────────────────────────────────────────────────────────────────

    return (
        <div className="space-y-6">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Invoices</h2>
                    <p className="text-slate-500 text-sm mt-1">Manage and track your invoices</p>
                </div>
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="icon" onClick={fetchInvoices} disabled={loading}>
                        <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    </Button>
                    <Link to="/invoices/new">
                        <Button className="bg-green-600 hover:bg-green-700">
                            <Plus className="h-4 w-4 mr-2" /> New Invoice
                        </Button>
                    </Link>
                </div>
            </div>

            {/* ── Stats Cards ───────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-slate-500">Total Invoices</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{stats.total}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-slate-500">Paid</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-green-600">{stats.paid}</div>
                        <p className="text-xs text-slate-400 mt-1">₹{stats.paidAmount.toLocaleString("en-IN")}</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-slate-500">Pending</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-blue-600">{stats.pending}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-slate-500">Overdue</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-red-600">{stats.overdue}</div>
                    </CardContent>
                </Card>
            </div>

            {/* ── Search + Filter Tabs ──────────────────────────────────────── */}
            <div className="flex flex-wrap items-center gap-4">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input
                        placeholder="Search invoices…"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                    />
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                    {TABS.map((tab) => (
                        <Button
                            key={tab}
                            variant={activeTab === tab ? "default" : "outline"}
                            size="sm"
                            onClick={() => setActiveTab(tab)}
                            className={
                                activeTab === tab
                                    ? "bg-green-600 hover:bg-green-700 capitalize"
                                    : "capitalize"
                            }
                        >
                            {tab}
                        </Button>
                    ))}
                </div>
            </div>

            {/* ── Invoice List ─────────────────────────────────────────────── */}
            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
                </div>
            ) : filteredInvoices.length === 0 ? (
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-16">
                        <div className="rounded-full bg-slate-100 p-6 mb-4">
                            <IndianRupee className="h-12 w-12 text-slate-400" />
                        </div>
                        <h3 className="text-xl font-semibold mb-2">No Invoices Found</h3>
                        <p className="text-slate-500 mb-6 text-center max-w-sm text-sm">
                            {activeTab === "all"
                                ? "Create your first invoice to get started with billing."
                                : `No ${activeTab} invoices found.`}
                        </p>
                        <Link to="/invoices/new">
                            <Button className="bg-green-600 hover:bg-green-700">
                                <Plus className="h-4 w-4 mr-2" /> Create Invoice
                            </Button>
                        </Link>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid gap-4">
                    {filteredInvoices.map((invoice) => (
                        <Card key={invoice.id} className="hover:shadow-md transition-shadow">
                            <CardHeader>
                                <div className="flex items-start justify-between">
                                    <div className="space-y-1">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            <h3 className="text-lg font-semibold">
                                                Invoice #{invoice.invoiceNumber}
                                            </h3>
                                            <Badge className={getStatusClass(invoice.status)}>
                                                {invoice.status}
                                            </Badge>
                                        </div>
                                        <p className="text-sm text-slate-500">
                                            {invoice.client?.name || invoice.description || "No client"}
                                        </p>
                                    </div>

                                    {/* Actions dropdown */}
                                    <DropdownMenu>
                                        <DropdownMenuTrigger asChild>
                                            <Button variant="ghost" size="icon">
                                                <MoreVertical className="h-4 w-4" />
                                            </Button>
                                        </DropdownMenuTrigger>
                                        <DropdownMenuContent align="end">
                                            <DropdownMenuItem onClick={() => handleViewInvoice(invoice)}>
                                                <Eye className="h-4 w-4 mr-2" /> View
                                            </DropdownMenuItem>
                                            <DropdownMenuItem
                                                onClick={() => handleSendInvoice(invoice)}
                                                disabled={actionLoading === invoice.id}
                                            >
                                                {actionLoading === invoice.id ? (
                                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                ) : (
                                                    <Send className="h-4 w-4 mr-2" />
                                                )}
                                                Send
                                            </DropdownMenuItem>
                                            <DropdownMenuItem
                                                onClick={() => handleDownloadInvoice(invoice)}
                                                disabled={actionLoading === invoice.id}
                                            >
                                                {actionLoading === invoice.id ? (
                                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                ) : (
                                                    <Download className="h-4 w-4 mr-2" />
                                                )}
                                                Download
                                            </DropdownMenuItem>
                                        </DropdownMenuContent>
                                    </DropdownMenu>
                                </div>
                            </CardHeader>

                            <CardContent>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                    <div>
                                        <p className="text-slate-400 mb-1">Amount</p>
                                        <p className="font-semibold text-base">
                                            ₹{invoice.total?.toLocaleString("en-IN")}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-slate-400 mb-1">Issue Date</p>
                                        <p className="font-medium">
                                            {new Date(invoice.issueDate).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-slate-400 mb-1">Due Date</p>
                                        <p className="font-medium">
                                            {new Date(invoice.dueDate).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-slate-400 mb-1">Payment</p>
                                        <p className="font-medium">
                                            {invoice.paidDate
                                                ? new Date(invoice.paidDate).toLocaleDateString()
                                                : "Not paid"}
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
