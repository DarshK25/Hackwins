import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { useAuth, useUser } from "@clerk/clerk-react";

const STATUS_STYLES = {
    paid: "mo-badge-success",
    sent: { backgroundColor: "#3B82F620", color: "#60A5FA", border: "1px solid #3B82F640", borderRadius: "6px", padding: "2px 8px", fontSize: "12px", fontWeight: "500", display: "inline-flex" },
    overdue: "mo-badge-danger",
    draft: "mo-badge-neutral",
};

const STATUS_BADGE_CLASS = (status) => {
    const s = status?.toLowerCase() || "draft";
    const map = {
        paid: "inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-[#4CBB1720] text-[#4CBB17] border border-[#4CBB1740]",
        sent: "inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-[#60A5FA20] text-[#60A5FA] border border-[#60A5FA40]",
        overdue: "inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-[#CD1C1820] text-[#CD1C18] border border-[#CD1C1840]",
        draft: "inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-[#A0A0A020] text-[#A0A0A0] border border-[#A0A0A040]",
    };
    return map[s] ?? map.draft;
};

const TABS = ["all", "draft", "sent", "paid", "overdue"];

export default function InvoicesPage() {
    const { getToken } = useAuth();
    const { user } = useUser();
    const navigate = useNavigate();
    const [invoices, setInvoices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState("all");
    const [searchQuery, setSearchQuery] = useState("");
    const [actionLoading, setActionLoading] = useState(null);

    useEffect(() => {
        if (user?.id) {
            fetchInvoices();
        }
    }, [user?.id]);

    const fetchInvoices = async () => {
        try {
            setLoading(true);
            const token = await getToken();
            const res = await fetch("/api/invoices", {
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": user?.id
                }
            });
            if (!res.ok) throw new Error("Failed to fetch");
            const data = await res.json();
            // Backend returns List<InvoiceDto> directly
            setInvoices(Array.isArray(data) ? data : []);
        } catch {
            toast.error("Failed to load invoices");
            setInvoices([]);
        } finally {
            setLoading(false);
        }
    };

    const handleViewInvoice = (invoice) => {
        const id = invoice.id || invoice._id;
        if (id) navigate(`/invoices/${id}`);
    };

    const handleSendInvoice = async (invoice) => {
        if (!invoice.clientEmail && !invoice.notes?.includes("@")) {
            toast.error("No email address found for this client");
            return;
        }
        setActionLoading(invoice.id || invoice._id);
        try {
            const token = await getToken();
            const id = invoice.id || invoice._id;
            const res = await fetch(`/api/invoices/${id}/send`, {
                method: "PATCH",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": user?.id
                }
            });
            if (!res.ok) throw new Error("Failed to send");
            toast.success(`Invoice sent to ${invoice.clientEmail || "client"}`);
            fetchInvoices();
        } catch (error) {
            toast.error(error?.message || "Failed to send invoice");
        } finally {
            setActionLoading(null);
        }
    };

    const handleDownloadInvoice = async (invoice) => {
        const id = invoice.id || invoice._id;
        setActionLoading(id);
        try {
            toast.info("Generating PDF…");
            const token = await getToken();
            const res = await fetch(`/api/invoices/${id}/download`, {
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": user?.id
                }
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

    const stats = {
        total: invoices.length,
        paid: invoices.filter((inv) => inv.status?.toLowerCase() === "paid").length,
        pending: invoices.filter((inv) => ["sent", "draft"].includes(inv.status?.toLowerCase())).length,
        overdue: invoices.filter((inv) => inv.status?.toLowerCase() === "overdue").length,
        paidAmount: invoices
            .filter((inv) => inv.status?.toLowerCase() === "paid")
            .reduce((sum, inv) => sum + (inv.totalAmount || 0), 0),
    };

    const filteredInvoices = invoices.filter((invoice) => {
        const statusMatch = activeTab === "all" || invoice.status?.toLowerCase() === activeTab;
        const searchMatch =
            !searchQuery ||
            invoice.invoiceNumber?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            invoice.clientName?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            invoice.notes?.toLowerCase().includes(searchQuery.toLowerCase());
        return statusMatch && searchMatch;
    });

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Invoices</h1>
                    <p className="mo-text-secondary mt-1">Manage and track your invoices</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        className="mo-btn-secondary flex items-center gap-2"
                        onClick={fetchInvoices}
                        disabled={loading}
                        aria-label="Refresh invoices"
                    >
                        <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <Link to="/invoices/new">
                        <button className="mo-btn-primary flex items-center gap-2">
                            <Plus className="h-4 w-4" /> New Invoice
                        </button>
                    </Link>
                </div>
            </div>

            {/* ── Stats ───────────────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-4">
                <div className="mo-stat-card">
                    <p className="text-sm text-[#A0A0A0] mb-2">Total Invoices</p>
                    <div className="text-3xl font-bold text-white">{stats.total}</div>
                </div>
                <div className="mo-stat-card">
                    <p className="text-sm text-[#A0A0A0] mb-2">Paid</p>
                    <div className="text-3xl font-bold text-[#4CBB17]">{stats.paid}</div>
                    <p className="text-xs text-[#A0A0A0] mt-1">₹{stats.paidAmount.toLocaleString("en-IN")}</p>
                </div>
                <div className="mo-stat-card">
                    <p className="text-sm text-[#A0A0A0] mb-2">Pending</p>
                    <div className="text-3xl font-bold text-white">{stats.pending}</div>
                </div>
                <div className="mo-stat-card">
                    <p className="text-sm text-[#A0A0A0] mb-2">Overdue</p>
                    <div className="text-3xl font-bold text-[#CD1C18]">{stats.overdue}</div>
                </div>
            </div>

            {/* ── Search + Tabs ───────────────────────────────────────────────── */}
            <div className="flex flex-wrap items-center gap-4">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#A0A0A0]" />
                    <input
                        placeholder="Search invoices…"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="mo-input w-full pl-10 pr-4 py-2 text-sm focus:outline-none"
                        style={{
                            backgroundColor: "#1A1A1A",
                            border: "1px solid #2A2A2A",
                            borderRadius: "8px",
                            color: "#ffffff",
                            width: "100%",
                        }}
                    />
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                    {TABS.map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium capitalize transition-all ${activeTab === tab
                                ? "bg-[#4CBB17] text-black"
                                : "bg-[#1A1A1A] text-[#A0A0A0] border border-[#2A2A2A] hover:border-[#4CBB17] hover:text-white"
                                }`}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
            </div>

            {/* ── Invoice List ─────────────────────────────────────────────────── */}
            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
                </div>
            ) : filteredInvoices.length === 0 ? (
                <div className="mo-card flex flex-col items-center justify-center py-16 border-dashed">
                    <div className="rounded-full bg-[#1A1A1A] p-6 mb-4 border border-[#2A2A2A]">
                        <IndianRupee className="h-12 w-12 text-[#A0A0A0]" />
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">No Invoices Found</h3>
                    <p className="text-[#A0A0A0] mb-6 text-center max-w-sm text-sm">
                        {activeTab === "all"
                            ? "Create your first invoice to get started with billing."
                            : `No ${activeTab} invoices found.`}
                    </p>
                    <Link to="/invoices/new">
                        <button className="mo-btn-primary flex items-center gap-2">
                            <Plus className="h-4 w-4" /> Create Invoice
                        </button>
                    </Link>
                </div>
            ) : (
                <div className="flex flex-col gap-3">
                    {filteredInvoices.map((invoice) => (
                        <div
                            key={invoice.id || invoice._id}
                            className="mo-card !py-4 cursor-pointer"
                            onClick={() => handleViewInvoice(invoice)}
                        >
                            <div className="flex items-start justify-between flex-wrap gap-4">
                                {/* Left */}
                                <div className="space-y-1.5">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <h3 className="text-base font-semibold text-white">
                                            Invoice #{invoice.invoiceNumber}
                                        </h3>
                                        <span className={STATUS_BADGE_CLASS(invoice.status)}>
                                            {invoice.status}
                                        </span>
                                    </div>
                                    <p className="text-sm text-[#A0A0A0]">
                                        {invoice.clientName || invoice.notes || "No client"}
                                    </p>
                                </div>

                                {/* Right */}
                                <div className="flex items-center gap-4">
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
                                        <div>
                                            <p className="text-[#A0A0A0] mb-0.5 text-xs">Amount</p>
                                            <p className="font-semibold text-white">
                                                ₹{invoice.totalAmount?.toLocaleString("en-IN")}
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-[#A0A0A0] mb-0.5 text-xs">Issue Date</p>
                                            <p className="font-medium text-white">
                                                {new Date(invoice.issueDate).toLocaleDateString()}
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-[#A0A0A0] mb-0.5 text-xs">Due Date</p>
                                            <p className="font-medium text-white">
                                                {new Date(invoice.dueDate).toLocaleDateString()}
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-[#A0A0A0] mb-0.5 text-xs">Payment</p>
                                            <p className="font-medium text-white">
                                                {invoice.paymentDate
                                                    ? new Date(invoice.paymentDate).toLocaleDateString()
                                                    : "Not paid"}
                                            </p>
                                        </div>
                                    </div>
                                    <div onClick={(e) => e.stopPropagation()}>
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <button className="p-2 rounded-lg hover:bg-[#2A2A2A] text-[#A0A0A0] hover:text-white transition-colors">
                                                    <MoreVertical className="h-4 w-4" />
                                                </button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end" className="bg-[#1A1A1A] border-[#2A2A2A]">
                                                <DropdownMenuItem
                                                    onClick={() => handleViewInvoice(invoice)}
                                                    className="text-white hover:bg-[#2A2A2A] cursor-pointer"
                                                >
                                                    <Eye className="h-4 w-4 mr-2" /> View
                                                </DropdownMenuItem>
                                                <DropdownMenuItem
                                                    onClick={(e) => { e.stopPropagation(); handleSendInvoice(invoice); }}
                                                    disabled={actionLoading === (invoice.id || invoice._id)}
                                                    className="text-white hover:bg-[#2A2A2A] cursor-pointer"
                                                >
                                                    {actionLoading === (invoice.id || invoice._id) ? (
                                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                    ) : (
                                                        <Send className="h-4 w-4 mr-2" />
                                                    )}
                                                    Send
                                                </DropdownMenuItem>
                                                <DropdownMenuItem
                                                    onClick={(e) => { e.stopPropagation(); handleDownloadInvoice(invoice); }}
                                                    disabled={actionLoading === (invoice.id || invoice._id)}
                                                    className="text-white hover:bg-[#2A2A2A] cursor-pointer"
                                                >
                                                    {actionLoading === (invoice.id || invoice._id) ? (
                                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                    ) : (
                                                        <Download className="h-4 w-4 mr-2" />
                                                    )}
                                                    Download
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
