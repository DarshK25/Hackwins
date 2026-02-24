import { useState, useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
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
    ArrowLeft,
    Send,
    FileText,
    Loader2,
    DollarSign,
    Trash2,
    IndianRupee,
    Printer,
    Mail,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_CLASSES = {
    PAID: "bg-green-500/10 text-green-600 hover:bg-green-500/20",
    SENT: "bg-blue-500/10 text-blue-600 hover:bg-blue-500/20",
    OVERDUE: "bg-red-500/10 text-red-600 hover:bg-red-500/20",
    DRAFT: "bg-slate-500/10 text-slate-500 hover:bg-slate-500/20",
};

const getStatusClass = (status) =>
    STATUS_CLASSES[status] ?? STATUS_CLASSES.DRAFT;

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InvoiceDetailPage() {
    const { getToken, isLoaded, isSignedIn, userId } = useAuth();
    const navigate = useNavigate();
    const { id } = useParams();

    const [invoice, setInvoice] = useState(null);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState(null);
    const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
    const [paymentForm, setPaymentForm] = useState({
        amount: "",
        paymentDate: new Date().toISOString().split("T")[0],
        paymentMethod: "bank_transfer",
    });

    useEffect(() => {
        if (isLoaded && isSignedIn && id) {
            fetchInvoice();
        }
    }, [isLoaded, isSignedIn, id]);

    // ── API ───────────────────────────────────────────────────────────────────

    const fetchInvoice = async () => {
        try {
            setLoading(true);
            const token = await getToken();
            const res = await fetch(`/api/invoices/${id}`, {
                headers: {
                    Authorization: `Bearer ${token}`,
                    "X-User-Id": userId,
                    "X-Org-Id": "placeholder-org"
                }
            });
            if (!res.ok) throw new Error("Failed to fetch invoice");
            const data = await res.json();
            setInvoice(data);
        } catch (error) {
            toast.error("Could not load invoice");
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const handleSend = async () => {
        setActionLoading("sending");
        try {
            const token = await getToken();
            const res = await fetch(`/api/invoices/${id}/send`, {
                method: "PATCH",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "X-User-Id": userId,
                    "X-Org-Id": "placeholder-org"
                }
            });
            if (!res.ok) throw new Error("Failed to send");
            toast.success("Invoice marked as sent");
            fetchInvoice();
        } catch (error) {
            toast.error("Failed to send invoice");
        } finally {
            setActionLoading(null);
        }
    };

    const handleMarkPaid = async (e) => {
        if (e) e.preventDefault();
        setActionLoading("paying");
        try {
            const token = await getToken();
            const res = await fetch(`/api/invoices/${id}/mark-paid`, {
                method: "PATCH",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "X-User-Id": userId,
                    "X-Org-Id": "placeholder-org"
                }
            });
            if (!res.ok) throw new Error("Failed to mark paid");
            toast.success("Invoice marked as paid");
            setPaymentDialogOpen(false);
            fetchInvoice();
        } catch (error) {
            toast.error("Failed to record payment");
        } finally {
            setActionLoading(null);
        }
    };

    const handleDelete = async () => {
        if (!window.confirm("Delete this invoice? This cannot be undone.")) return;
        setActionLoading("deleting");
        try {
            const token = await getToken();
            const res = await fetch(`/api/invoices/${id}`, {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "X-User-Id": userId,
                    "X-Org-Id": "placeholder-org"
                }
            });
            if (!res.ok) throw new Error("Failed to delete");
            toast.success("Invoice deleted");
            navigate("/invoices");
        } catch (error) {
            toast.error("Failed to delete invoice");
        } finally {
            setActionLoading(null);
        }
    };

    // ── Render Helpers ────────────────────────────────────────────────────────

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-96 space-y-4">
                <Loader2 className="h-8 w-8 animate-spin text-green-600" />
                <p className="text-slate-500 text-sm">Loading invoice data...</p>
            </div>
        );
    }

    if (!invoice) {
        return (
            <Card className="max-w-md mx-auto mt-12 overflow-hidden border-dashed">
                <CardContent className="flex flex-col items-center justify-center py-12">
                    <div className="rounded-full bg-slate-100 p-4 mb-4">
                        <FileText className="h-10 w-10 text-slate-400" />
                    </div>
                    <h3 className="text-xl font-bold mb-2">Invoice Not Found</h3>
                    <p className="text-slate-500 text-sm text-center mb-6">
                        The invoice you're looking for doesn't exist or you don't have access.
                    </p>
                    <Button onClick={() => navigate("/invoices")} variant="outline">
                        Back to List
                    </Button>
                </CardContent>
            </Card>
        );
    }

    const totalPaid = invoice.status === "PAID" ? Number(invoice.totalAmount) : 0;
    const remaining = Number(invoice.totalAmount) - totalPaid;

    return (
        <div className="space-y-6">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => navigate("/invoices")}>
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <div className="flex items-center gap-2">
                            <h2 className="text-2xl font-bold font-mono">#{invoice.invoiceNumber}</h2>
                            <Badge className={getStatusClass(invoice.status)}>
                                {invoice.status}
                            </Badge>
                        </div>
                        <p className="text-sm font-semibold text-green-600 mt-1">
                            Client: {invoice.clientName || "Unknown Client"}
                        </p>
                        <p className="text-xs text-slate-500">
                            Issued on {new Date(invoice.issueDate).toLocaleDateString()}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => window.print()}>
                        <Printer className="h-4 w-4 mr-2" /> Print
                    </Button>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleSend}
                        disabled={actionLoading === "sending" || invoice.status === "PAID"}
                    >
                        {actionLoading === "sending" ? <Loader2 className="animate-spin h-4 w-4 mr-2" /> : <Mail className="h-4 w-4 mr-2" />}
                        {invoice.status === "DRAFT" ? "Mark as Sent" : "Resend"}
                    </Button>
                    <Button
                        variant="destructive"
                        size="sm"
                        onClick={handleDelete}
                        disabled={actionLoading === "deleting"}
                    >
                        <Trash2 className="h-4 w-4 mr-2" /> Delete
                    </Button>
                </div>
            </div>

            {/* ── Main Layout ─────────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Left: Invoice Details (2 cols) */}
                <div className="lg:col-span-2 space-y-6">
                    <Card>
                        <CardHeader className="border-b pb-4">
                            <div className="flex items-center justify-between">
                                <div className="space-y-1">
                                    <CardTitle className="text-lg">Billing Details</CardTitle>
                                    <p className="text-sm font-medium text-slate-900">
                                        Bill To: {invoice.clientName || "N/A"}
                                    </p>
                                    {invoice.clientCompany && (
                                        <p className="text-xs text-slate-500">{invoice.clientCompany}</p>
                                    )}
                                    {invoice.clientEmail && (
                                        <p className="text-xs text-slate-500">{invoice.clientEmail}</p>
                                    )}
                                    {invoice.clientPhone && (
                                        <p className="text-xs text-slate-500">{invoice.clientPhone}</p>
                                    )}
                                </div>
                                <div className="text-right">
                                    <p className="text-xs text-slate-500 uppercase font-semibold">Due Date</p>
                                    <p className="text-sm font-bold text-red-600">
                                        {new Date(invoice.dueDate).toLocaleDateString()}
                                    </p>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="pt-6 space-y-8">
                            {/* Line Items Table */}
                            <div className="overflow-x-auto rounded-lg border">
                                <table className="w-full text-sm">
                                    <thead className="bg-slate-50 text-slate-600 uppercase text-[10px] font-bold">
                                        <tr>
                                            <th className="px-4 py-3 text-left">Description</th>
                                            <th className="px-4 py-3 text-center">Qty</th>
                                            <th className="px-4 py-3 text-right">Rate</th>
                                            <th className="px-4 py-3 text-right">Tax (%)</th>
                                            <th className="px-4 py-3 text-right">Total</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y">
                                        {invoice.items?.map((item, idx) => (
                                            <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                                                <td className="px-4 py-4 font-medium">{item.description}</td>
                                                <td className="px-4 py-4 text-center">{item.quantity}</td>
                                                <td className="px-4 py-4 text-right">₹{Number(item.rate).toLocaleString()}</td>
                                                <td className="px-4 py-4 text-right">{item.gstPercent}%</td>
                                                <td className="px-4 py-4 text-right font-bold text-slate-900">
                                                    ₹{Number(item.lineTotal).toLocaleString()}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            {/* Summary Totals */}
                            <div className="flex justify-end pt-4">
                                <div className="w-full max-w-[280px] space-y-3">
                                    <div className="flex justify-between text-sm text-slate-600">
                                        <span>Subtotal</span>
                                        <span>₹{Number(invoice.subtotal).toLocaleString()}</span>
                                    </div>
                                    <div className="flex justify-between text-sm text-slate-600 pb-3 border-b border-dashed">
                                        <span>Total GST</span>
                                        <span>₹{Number(invoice.gstTotal).toLocaleString()}</span>
                                    </div>
                                    <div className="flex justify-between items-center text-lg font-black text-slate-900">
                                        <span>Grand Total</span>
                                        <div className="flex items-center text-green-700">
                                            <IndianRupee className="h-4 w-4 mr-0.5" />
                                            {Number(invoice.totalAmount).toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {invoice.notes && (
                        <Card className="border-l-4 border-l-blue-500">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-sm font-semibold text-slate-500 uppercase">Notes</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <p className="text-sm text-slate-700 leading-relaxed italic">{invoice.notes}</p>
                            </CardContent>
                        </Card>
                    )}
                </div>

                {/* Right: Payment Sidebar (1 col) */}
                <div className="space-y-6">
                    <Card className="bg-slate-900 text-white border-0 shadow-xl overflow-hidden relative">
                        {/* Abstract background glow */}
                        <div className="absolute -right-16 -top-16 w-32 h-32 bg-green-500/20 blur-3xl" />

                        <CardHeader>
                            <CardTitle className="text-lg text-slate-300">Payment Status</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="space-y-1">
                                <p className="text-xs text-slate-400 uppercase font-bold tracking-wider">Remaining Balance</p>
                                <h3 className="text-3xl font-black">
                                    ₹{remaining.toLocaleString()}
                                </h3>
                            </div>

                            <div className="space-y-3 pt-2">
                                <div className="w-full bg-slate-800 rounded-full h-2">
                                    <div
                                        className="bg-green-500 h-2 rounded-full transition-all duration-1000"
                                        style={{
                                            width: invoice.totalAmount > 0
                                                ? `${(totalPaid / Number(invoice.totalAmount)) * 100}%`
                                                : "0%"
                                        }}
                                    />
                                </div>
                                <div className="flex justify-between text-xs text-slate-400 font-medium">
                                    <span>Paid: ₹{totalPaid.toLocaleString()}</span>
                                    <span>Total: ₹{Number(invoice.totalAmount).toLocaleString()}</span>
                                </div>
                            </div>

                            {invoice.status !== "PAID" && (
                                <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
                                    <DialogTrigger asChild>
                                        <Button className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-6">
                                            <DollarSign className="h-5 w-5 mr-2" /> Record Payment
                                        </Button>
                                    </DialogTrigger>
                                    <DialogContent>
                                        <DialogHeader>
                                            <DialogTitle>Mark as Paid</DialogTitle>
                                        </DialogHeader>
                                        <div className="space-y-4 py-4 uppercase">
                                            <p className="text-sm text-slate-500">
                                                This will record the full amount (₹{Number(invoice.totalAmount).toLocaleString()}) as received and mark the invoice as PAID.
                                            </p>
                                            <Button
                                                className="w-full py-6 text-lg font-bold"
                                                onClick={handleMarkPaid}
                                                disabled={actionLoading === "paying"}
                                            >
                                                {actionLoading === "paying" ? <Loader2 className="animate-spin h-5 w-5 mr-2" /> : "Confirm Full Payment"}
                                            </Button>
                                        </div>
                                    </DialogContent>
                                </Dialog>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="text-sm font-semibold text-slate-500 uppercase">Audit & Logs</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="flex items-center gap-3">
                                <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center">
                                    <FileText className="h-4 w-4 text-slate-600" />
                                </div>
                                <div className="text-xs">
                                    <p className="font-bold text-slate-900">Invoice Created</p>
                                    <p className="text-slate-500">{new Date(invoice.issueDate).toLocaleDateString()}</p>
                                </div>
                            </div>
                            {invoice.paymentDate && (
                                <div className="flex items-center gap-3">
                                    <div className="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
                                        <DollarSign className="h-4 w-4 text-green-600" />
                                    </div>
                                    <div className="text-xs">
                                        <p className="font-bold text-slate-900">Payment Received</p>
                                        <p className="text-slate-500">{new Date(invoice.paymentDate).toLocaleDateString()}</p>
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
