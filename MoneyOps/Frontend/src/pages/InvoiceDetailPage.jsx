import { useState, useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
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
} from "lucide-react";
import { toast } from "sonner";

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_BADGE_CLASSES = {
    paid: "bg-green-100 text-green-800",
    sent: "bg-blue-100 text-blue-800",
    draft: "bg-slate-100 text-slate-700",
};

const getStatusClass = (status) =>
    STATUS_BADGE_CLASSES[status] ?? "bg-slate-100 text-slate-700";

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InvoiceDetailPage() {
    const navigate = useNavigate();
    const { id } = useParams();

    const [invoice, setInvoice] = useState(null);
    const [logs, setLogs] = useState([]);
    const [payments, setPayments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sending, setSending] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [paymentDialogOpen, setPaymentDialogOpen] = useState(false);
    const [paymentForm, setPaymentForm] = useState({
        amount: "",
        paymentDate: new Date().toISOString().split("T")[0],
        paymentMethod: "bank_transfer",
        transactionId: "",
        notes: "",
    });

    useEffect(() => {
        if (id) {
            fetchInvoice(id);
            fetchLogs(id);
            fetchPayments(id);
        }
    }, [id]);

    // ── API ───────────────────────────────────────────────────────────────────

    const fetchInvoice = async (invoiceId) => {
        try {
            const res = await fetch(`/api/invoices/${invoiceId}`);
            if (!res.ok) throw new Error("Failed to fetch invoice");
            const data = await res.json();
            setInvoice(data);
        } catch (error) {
            console.error(error);
            toast.error("Could not load invoice");
        } finally {
            setLoading(false);
        }
    };

    const fetchLogs = async (invoiceId) => {
        try {
            const res = await fetch(`/api/invoices/${invoiceId}/logs`);
            if (res.ok) setLogs(await res.json());
        } catch (error) {
            console.error(error);
        }
    };

    const fetchPayments = async (invoiceId) => {
        try {
            const res = await fetch(`/api/invoices/${invoiceId}/payment`);
            if (res.ok) setPayments(await res.json());
        } catch (error) {
            console.error(error);
        }
    };

    const handleRecordPayment = async (e) => {
        e.preventDefault();
        try {
            const res = await fetch(`/api/invoices/${invoice.id}/payment`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    amount: parseFloat(paymentForm.amount),
                    paymentDate: paymentForm.paymentDate,
                    paymentMethod: paymentForm.paymentMethod,
                    transactionId: paymentForm.transactionId,
                    notes: paymentForm.notes,
                }),
            });

            if (!res.ok) throw new Error("Failed to record payment");

            const result = await res.json();
            toast.success(result.message);
            setPaymentDialogOpen(false);
            setPaymentForm({
                amount: "",
                paymentDate: new Date().toISOString().split("T")[0],
                paymentMethod: "bank_transfer",
                transactionId: "",
                notes: "",
            });
            fetchInvoice(invoice.id);
            fetchPayments(invoice.id);
            fetchLogs(invoice.id);
        } catch (error) {
            toast.error(error?.message || "Failed to record payment");
        }
    };

    const handleSend = async () => {
        setSending(true);
        try {
            await new Promise((resolve) => setTimeout(resolve, 1000));
            toast.success("Invoice sent successfully");
        } catch (error) {
            toast.error(error?.message || "Failed to send invoice");
        } finally {
            setSending(false);
        }
    };

    const handleDelete = async () => {
        if (!window.confirm("Delete this invoice? This cannot be undone.")) return;

        setDeleting(true);
        try {
            const res = await fetch(`/api/invoices/${invoice.id}`, { method: "DELETE" });
            if (!res.ok) throw new Error("Failed to delete invoice");

            toast.success("Invoice deleted successfully");
            navigate("/invoices");
        } catch (error) {
            toast.error(error?.message || "Failed to delete invoice");
            setDeleting(false);
        }
    };

    // ── Derived state ─────────────────────────────────────────────────────────

    const totalPaid = payments.reduce((sum, p) => sum + parseFloat(p.amount), 0);
    const remainingAmount = invoice ? parseFloat(invoice.total) - totalPaid : 0;

    // ── Loading / not found ───────────────────────────────────────────────────

    if (loading) {
        return (
            <div className="flex justify-center items-center h-96">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
        );
    }

    if (!invoice) {
        return (
            <div className="flex flex-col justify-center items-center h-96 gap-4">
                <p className="text-slate-500">Invoice not found</p>
                <Link to="/invoices" className="text-blue-600 underline text-sm">
                    Back to Invoices
                </Link>
            </div>
        );
    }

    // ── Render ────────────────────────────────────────────────────────────────

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div className="flex flex-wrap justify-between items-center gap-4">
                <div className="flex items-center gap-3 flex-wrap">
                    <Link to="/invoices" className="text-slate-400 hover:text-slate-700">
                        <ArrowLeft className="h-4 w-4" />
                    </Link>
                    <h2 className="text-3xl font-bold tracking-tight">
                        Invoice {invoice.invoiceNumber}
                    </h2>
                    <span
                        className={`px-2.5 py-1 rounded-full text-xs font-semibold ${getStatusClass(invoice.status)}`}
                    >
                        {invoice.status?.toUpperCase()}
                    </span>
                </div>

                <div className="flex flex-wrap gap-2">
                    <Button variant="outline" onClick={() => window.print()}>
                        <FileText className="mr-2 h-4 w-4" /> Export PDF
                    </Button>
                    <Button
                        variant="outline"
                        onClick={handleSend}
                        disabled={sending || invoice.status === "paid"}
                    >
                        {sending ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                            <Send className="mr-2 h-4 w-4" />
                        )}
                        Send Invoice
                    </Button>
                    <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
                        {deleting ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                            <Trash2 className="mr-2 h-4 w-4" />
                        )}
                        Delete
                    </Button>

                    {invoice.status !== "paid" && (
                        <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
                            <DialogTrigger asChild>
                                <Button>
                                    <DollarSign className="mr-2 h-4 w-4" />
                                    Record Payment
                                </Button>
                            </DialogTrigger>
                            <DialogContent>
                                <DialogHeader>
                                    <DialogTitle>Record Payment</DialogTitle>
                                </DialogHeader>
                                <form onSubmit={handleRecordPayment} className="space-y-4 mt-2">
                                    <div className="space-y-2">
                                        <Label htmlFor="pay-amount">Amount *</Label>
                                        <Input
                                            id="pay-amount"
                                            type="number"
                                            step="0.01"
                                            value={paymentForm.amount}
                                            onChange={(e) =>
                                                setPaymentForm((p) => ({ ...p, amount: e.target.value }))
                                            }
                                            placeholder={`Remaining: ₹${remainingAmount.toFixed(2)}`}
                                            required
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="pay-date">Payment Date *</Label>
                                        <Input
                                            id="pay-date"
                                            type="date"
                                            value={paymentForm.paymentDate}
                                            onChange={(e) =>
                                                setPaymentForm((p) => ({ ...p, paymentDate: e.target.value }))
                                            }
                                            required
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="pay-method">Payment Method *</Label>
                                        <Select
                                            value={paymentForm.paymentMethod}
                                            onValueChange={(value) =>
                                                setPaymentForm((p) => ({ ...p, paymentMethod: value }))
                                            }
                                        >
                                            <SelectTrigger id="pay-method">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="cash">Cash</SelectItem>
                                                <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                                                <SelectItem value="upi">UPI</SelectItem>
                                                <SelectItem value="card">Card</SelectItem>
                                                <SelectItem value="cheque">Cheque</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="pay-txn">Transaction ID</Label>
                                        <Input
                                            id="pay-txn"
                                            value={paymentForm.transactionId}
                                            onChange={(e) =>
                                                setPaymentForm((p) => ({ ...p, transactionId: e.target.value }))
                                            }
                                            placeholder="Optional"
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="pay-notes">Notes</Label>
                                        <Input
                                            id="pay-notes"
                                            value={paymentForm.notes}
                                            onChange={(e) =>
                                                setPaymentForm((p) => ({ ...p, notes: e.target.value }))
                                            }
                                            placeholder="Optional"
                                        />
                                    </div>
                                    <Button type="submit" className="w-full">
                                        Record Payment
                                    </Button>
                                </form>
                            </DialogContent>
                        </Dialog>
                    )}
                </div>
            </div>

            {/* ── Main Content ───────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

                {/* Left — invoice details */}
                <div className="lg:col-span-2 space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Invoice Details</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {/* Meta */}
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <p className="text-slate-400 mb-1">Customer</p>
                                    <p className="font-medium">{invoice.customerName}</p>
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
                                    <p className="text-slate-400 mb-1">Total Amount</p>
                                    <p className="font-semibold text-base">₹{invoice.total}</p>
                                </div>
                            </div>

                            {/* Line items table */}
                            <div>
                                <h3 className="font-semibold mb-3">Items</h3>
                                <div className="border rounded-lg overflow-hidden">
                                    <table className="w-full text-sm">
                                        <thead className="bg-slate-50">
                                            <tr>
                                                <th className="p-3 text-left font-medium text-slate-600">Description</th>
                                                <th className="p-3 text-right font-medium text-slate-600">Qty</th>
                                                <th className="p-3 text-right font-medium text-slate-600">Rate</th>
                                                <th className="p-3 text-right font-medium text-slate-600">Amount</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {Array.isArray(invoice.lineItems) &&
                                                invoice.lineItems.map((item, i) => (
                                                    <tr key={i} className="border-t">
                                                        <td className="p-3">{item.description}</td>
                                                        <td className="p-3 text-right">{item.quantity}</td>
                                                        <td className="p-3 text-right">₹{item.rate}</td>
                                                        <td className="p-3 text-right">₹{item.amount}</td>
                                                    </tr>
                                                ))}
                                        </tbody>
                                    </table>
                                </div>

                                {/* Totals */}
                                <div className="flex justify-end mt-4">
                                    <div className="w-48 space-y-1 text-sm">
                                        <div className="flex justify-between py-1">
                                            <span className="text-slate-400">Subtotal</span>
                                            <span>₹{invoice.amount}</span>
                                        </div>
                                        <div className="flex justify-between py-1">
                                            <span className="text-slate-400">Tax</span>
                                            <span>₹{invoice.tax}</span>
                                        </div>
                                        <div className="flex justify-between py-1.5 font-bold border-t mt-1">
                                            <span>Total</span>
                                            <span>₹{invoice.total}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right — payment sidebar */}
                <div className="space-y-6">
                    {/* Payment Summary */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Payment Summary</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3 text-sm">
                            <div className="flex justify-between">
                                <span className="text-slate-400">Invoice Total</span>
                                <span className="font-medium">₹{invoice.total}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-400">Total Paid</span>
                                <span className="font-medium text-green-600">₹{totalPaid.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between border-t pt-3">
                                <span className="font-semibold">Remaining</span>
                                <span
                                    className={`font-bold ${remainingAmount > 0 ? "text-orange-600" : "text-green-600"
                                        }`}
                                >
                                    ₹{remainingAmount.toFixed(2)}
                                </span>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Payment History */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Payment History</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {payments.length === 0 ? (
                                    <p className="text-slate-400 text-sm">No payments recorded yet.</p>
                                ) : (
                                    payments.map((payment) => (
                                        <div
                                            key={payment.id}
                                            className="flex gap-3 text-sm border-b pb-3 last:border-0"
                                        >
                                            <div className="w-2 h-2 mt-1.5 rounded-full bg-green-500 shrink-0" />
                                            <div className="flex-1">
                                                <div className="flex justify-between">
                                                    <p className="font-medium">₹{payment.amount.toFixed(2)}</p>
                                                    <span className="text-xs text-slate-400 capitalize">
                                                        {payment.paymentMethod?.replace("_", " ")}
                                                    </span>
                                                </div>
                                                <p className="text-xs text-slate-400">
                                                    {new Date(payment.paymentDate).toLocaleDateString()}
                                                </p>
                                                {payment.transactionId && (
                                                    <p className="text-xs text-slate-400 mt-1">
                                                        Txn: {payment.transactionId}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Audit Log */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Audit Log</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                {logs.length === 0 ? (
                                    <p className="text-slate-400 text-sm">No logs found.</p>
                                ) : (
                                    logs.map((log) => (
                                        <div key={log.id} className="flex gap-3 text-sm">
                                            <div className="w-2 h-2 mt-1.5 rounded-full bg-blue-500 shrink-0" />
                                            <div>
                                                <p className="font-medium capitalize">
                                                    {log.action?.replace("_", " ")}
                                                </p>
                                                <p className="text-xs text-slate-400">
                                                    {new Date(log.createdAt).toLocaleString()}
                                                </p>
                                                {log.details && (
                                                    <p className="text-xs text-slate-400 mt-1">
                                                        {JSON.stringify(log.details).slice(0, 50)}…
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}
