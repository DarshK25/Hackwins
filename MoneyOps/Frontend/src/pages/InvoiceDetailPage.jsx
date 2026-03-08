import { useState, useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { ArrowLeft, Send, FileText, Loader2, DollarSign, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useAuth, useUser } from "@clerk/clerk-react";

const STATUS_BADGE = {
    paid: "bg-[#4CBB1720] text-[#4CBB17] border-[#4CBB1740]",
    sent: "bg-[#60A5FA20] text-[#60A5FA] border-[#60A5FA40]",
    draft: "bg-[#A0A0A020] text-[#A0A0A0] border-[#A0A0A040]",
};
const getStatusBadge = (s) => STATUS_BADGE[s?.toLowerCase()] ?? STATUS_BADGE.draft;

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

export default function InvoiceDetailPage() {
    const { getToken } = useAuth();
    const { user } = useUser();
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
        if (id && user?.id) {
            fetchInvoice(id);
            fetchLogs(id);
            fetchPayments(id);
        }
    }, [id, user?.id]);

    const fetchInvoice = async (invoiceId) => {
        try {
            const token = await getToken();
            const res = await fetch(`/api/invoices/${invoiceId}`, {
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": user?.id
                }
            });
            if (!res.ok) throw new Error("Failed to fetch invoice");
            setInvoice(await res.json());
        } catch (error) {
            console.error(error);
            toast.error("Could not load invoice");
        } finally { setLoading(false); }
    };

    const fetchLogs = async (invoiceId) => {
        try {
            const token = await getToken();
            const res = await fetch(`/api/invoices/${invoiceId}/logs`, {
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": user?.id
                }
            });
            if (res.ok) setLogs(await res.json());
        } catch (error) { console.error(error); }
    };

    const fetchPayments = async (invoiceId) => {
        try {
            const token = await getToken();
            const res = await fetch(`/api/invoices/${invoiceId}/payment`, {
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": user?.id
                }
            });
            if (res.ok) setPayments(await res.json());
        } catch (error) { console.error(error); }
    };

    const handleRecordPayment = async (e) => {
        e.preventDefault();
        try {
            const token = await getToken();
            const res = await fetch(`/api/invoices/${invoice.id}/payment`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": user?.id
                },
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
            setPaymentForm({ amount: "", paymentDate: new Date().toISOString().split("T")[0], paymentMethod: "bank_transfer", transactionId: "", notes: "" });
            fetchInvoice(invoice.id);
            fetchPayments(invoice.id);
            fetchLogs(invoice.id);
        } catch (error) { toast.error(error?.message || "Failed to record payment"); }
    };

    const handleSend = async () => {
        setSending(true);
        try {
            const token = await getToken();
            const res = await fetch(`/api/invoices/${invoice.id}/send`, {
                method: "PATCH",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": user?.id
                }
            });
            if (!res.ok) throw new Error("Failed to send invoice");
            const updated = await res.json();
            setInvoice(updated);
            toast.success("Invoice sent successfully");
            fetchLogs(invoice.id);
        } catch (error) { toast.error(error?.message || "Failed to send invoice"); }
        finally { setSending(false); }
    };

    const handleDelete = async () => {
        if (!window.confirm("Delete this invoice? This cannot be undone.")) return;
        setDeleting(true);
        try {
            const token = await getToken();
            const res = await fetch(`/api/invoices/${invoice.id}`, {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": user?.id
                }
            });
            if (!res.ok) throw new Error("Failed to delete invoice");
            toast.success("Invoice deleted successfully");
            navigate("/invoices");
        } catch (error) {
            toast.error(error?.message || "Failed to delete invoice");
            setDeleting(false);
        }
    };

    const totalPaid = payments.reduce((sum, p) => sum + parseFloat(p.amount), 0);
    const remainingAmount = invoice ? parseFloat(invoice.totalAmount || 0) - totalPaid : 0;

    if (loading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
            </div>
        );
    }

    if (!invoice) {
        return (
            <div className="flex flex-col justify-center items-center h-64 gap-4">
                <p className="text-[#A0A0A0]">Invoice not found</p>
                <Link to="/invoices" className="text-[#4CBB17] text-sm hover:underline">Back to Invoices</Link>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="flex flex-wrap justify-between items-center gap-4">
                <div className="flex items-center gap-3 flex-wrap">
                    <Link to="/invoices" className="text-[#A0A0A0] hover:text-[#4CBB17] transition-colors">
                        <ArrowLeft className="h-4 w-4" />
                    </Link>
                    <h1 className="mo-h1">Invoice {invoice.invoiceNumber}</h1>
                    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${getStatusBadge(invoice.status)}`}>
                        {invoice.status?.toUpperCase()}
                    </span>
                </div>

                <div className="flex flex-wrap gap-2">
                    <button className="mo-btn-secondary flex items-center gap-2 text-sm" onClick={() => window.print()}>
                        <FileText className="h-4 w-4" /> Export PDF
                    </button>
                    <button
                        className="mo-btn-secondary flex items-center gap-2 text-sm disabled:opacity-40"
                        onClick={handleSend}
                        disabled={sending || invoice.status === "paid"}
                    >
                        {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                        Send Invoice
                    </button>
                    <button
                        className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-[#CD1C1820] text-[#CD1C18] border border-[#CD1C1840] hover:bg-[#CD1C1830] transition-all disabled:opacity-40"
                        onClick={handleDelete}
                        disabled={deleting}
                    >
                        {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                        Delete
                    </button>

                    {invoice.status !== "paid" && (
                        <Dialog open={paymentDialogOpen} onOpenChange={setPaymentDialogOpen}>
                            <DialogTrigger asChild>
                                <button className="mo-btn-primary flex items-center gap-2 text-sm">
                                    <DollarSign className="h-4 w-4" /> Record Payment
                                </button>
                            </DialogTrigger>
                            <DialogContent className="sm:max-w-md bg-[#111111] border-[#2A2A2A]">
                                <DialogHeader>
                                    <DialogTitle className="text-white">Record Payment</DialogTitle>
                                </DialogHeader>
                                <form onSubmit={handleRecordPayment} className="flex flex-col gap-4 mt-2">
                                    <div>
                                        <label htmlFor="pay-amount" className="text-sm text-[#A0A0A0] block mb-1.5">Amount *</label>
                                        <DarkInput id="pay-amount" type="number" step="0.01" value={paymentForm.amount} onChange={(e) => setPaymentForm((p) => ({ ...p, amount: e.target.value }))} placeholder={`Remaining: ₹${remainingAmount.toFixed(2)}`} required />
                                    </div>
                                    <div>
                                        <label htmlFor="pay-date" className="text-sm text-[#A0A0A0] block mb-1.5">Payment Date *</label>
                                        <DarkInput id="pay-date" type="date" value={paymentForm.paymentDate} onChange={(e) => setPaymentForm((p) => ({ ...p, paymentDate: e.target.value }))} required />
                                    </div>
                                    <div>
                                        <label htmlFor="pay-method" className="text-sm text-[#A0A0A0] block mb-1.5">Payment Method *</label>
                                        <Select value={paymentForm.paymentMethod} onValueChange={(val) => setPaymentForm((p) => ({ ...p, paymentMethod: val }))}>
                                            <SelectTrigger id="pay-method" className="bg-[#1A1A1A] border-[#2A2A2A] text-white">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                                {["cash", "bank_transfer", "upi", "card", "cheque"].map((m) => (
                                                    <SelectItem key={m} value={m} className="text-white focus:bg-[#2A2A2A] capitalize">{m.replace("_", " ")}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    <div>
                                        <label htmlFor="pay-txn" className="text-sm text-[#A0A0A0] block mb-1.5">Transaction ID</label>
                                        <DarkInput id="pay-txn" value={paymentForm.transactionId} onChange={(e) => setPaymentForm((p) => ({ ...p, transactionId: e.target.value }))} placeholder="Optional" />
                                    </div>
                                    <div>
                                        <label htmlFor="pay-notes" className="text-sm text-[#A0A0A0] block mb-1.5">Notes</label>
                                        <DarkInput id="pay-notes" value={paymentForm.notes} onChange={(e) => setPaymentForm((p) => ({ ...p, notes: e.target.value }))} placeholder="Optional" />
                                    </div>
                                    <button type="submit" className="mo-btn-primary w-full">Record Payment</button>
                                </form>
                            </DialogContent>
                        </Dialog>
                    )}
                </div>
            </div>

            {/* ── Main Content ──────────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left — invoice details */}
                <div className="lg:col-span-2 flex flex-col gap-5">
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-5">Invoice Details</h2>
                        <div className="grid grid-cols-2 gap-4 text-sm mb-6">
                            {[
                                { label: "Customer", value: invoice.clientName || "N/A" },
                                { label: "Issue Date", value: invoice.issueDate ? new Date(invoice.issueDate).toLocaleDateString() : "N/A" },
                                { label: "Due Date", value: invoice.dueDate ? new Date(invoice.dueDate).toLocaleDateString() : "N/A" },
                                { label: "Total Amount", value: `₹${(invoice.totalAmount || 0).toLocaleString("en-IN")}`, highlight: true },
                            ].map(({ label, value, highlight }) => (
                                <div key={label}>
                                    <p className="text-[#A0A0A0] text-xs mb-1">{label}</p>
                                    <p className={`font-semibold ${highlight ? "text-[#4CBB17] text-base" : "text-white"}`}>{value}</p>
                                </div>
                            ))}
                        </div>

                        {/* Line Items Table */}
                        <h3 className="font-semibold text-white mb-3">Items</h3>
                        <div className="rounded-xl overflow-hidden border border-[#2A2A2A]">
                            <table className="w-full text-sm">
                                <thead className="bg-[#1A1A1A]">
                                    <tr>
                                        {["Description", "Qty", "Rate", "Amount"].map((h, i) => (
                                            <th key={h} className={`p-3 font-medium text-[#A0A0A0] ${i === 0 ? "text-left" : "text-right"}`}>{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[#2A2A2A]">
                                    {Array.isArray(invoice.items) && invoice.items.map((item, i) => (
                                        <tr key={i} className="hover:bg-[#1A1A1A] transition-colors">
                                            <td className="p-3 text-white">{item.description}</td>
                                            <td className="p-3 text-right text-[#A0A0A0]">{item.quantity || "-"}</td>
                                            <td className="p-3 text-right text-[#A0A0A0]">₹{item.rate}</td>
                                            <td className="p-3 text-right font-medium text-white">₹{item.lineTotal}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <div className="flex justify-end mt-4">
                            <div className="w-48 flex flex-col gap-1 text-sm">
                                <div className="flex justify-between py-1"><span className="text-[#A0A0A0]">Subtotal</span><span className="text-white">₹{(invoice.subtotal || 0).toLocaleString("en-IN")}</span></div>
                                <div className="flex justify-between py-1"><span className="text-[#A0A0A0]">GST Total</span><span className="text-white">₹{(invoice.gstTotal || 0).toLocaleString("en-IN")}</span></div>
                                <div className="flex justify-between py-2 font-bold border-t border-[#2A2A2A] mt-1">
                                    <span className="text-white">Total</span>
                                    <span className="text-[#4CBB17]">₹{(invoice.totalAmount || 0).toLocaleString("en-IN")}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Right — sidebar */}
                <div className="flex flex-col gap-5">
                    {/* Payment Summary */}
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-4">Payment Summary</h2>
                        <div className="flex flex-col gap-2 text-sm">
                            <div className="flex justify-between"><span className="text-[#A0A0A0]">Invoice Total</span><span className="font-medium text-white">₹{(invoice.totalAmount || 0).toLocaleString("en-IN")}</span></div>
                            <div className="flex justify-between"><span className="text-[#A0A0A0]">Total Paid</span><span className="font-medium text-[#4CBB17]">₹{totalPaid.toFixed(2)}</span></div>
                            <div className="flex justify-between border-t border-[#2A2A2A] pt-3 mt-1">
                                <span className="font-semibold text-white">Remaining</span>
                                <span className={`font-bold ${remainingAmount > 0 ? "text-[#FFB300]" : "text-[#4CBB17]"}`}>₹{remainingAmount.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>

                    {/* Payment History */}
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-4">Payment History</h2>
                        {payments.length === 0 ? (
                            <p className="text-[#A0A0A0] text-sm">No payments recorded yet.</p>
                        ) : (
                            <div className="flex flex-col gap-3">
                                {payments.map((payment) => (
                                    <div key={payment.id} className="flex gap-3 text-sm pb-3 border-b border-[#2A2A2A] last:border-0">
                                        <div className="w-2 h-2 mt-1.5 rounded-full bg-[#4CBB17] shrink-0" />
                                        <div className="flex-1">
                                            <div className="flex justify-between">
                                                <p className="font-semibold text-white">₹{(payment.amount || 0).toLocaleString("en-IN")}</p>
                                                <span className="text-xs text-[#A0A0A0] capitalize">{payment.paymentMethod?.replace("_", " ")}</span>
                                            </div>
                                            <p className="text-xs text-[#A0A0A0]">{new Date(payment.paymentDate).toLocaleDateString()}</p>
                                            {payment.transactionId && <p className="text-xs text-[#A0A0A0] mt-0.5">Txn: {payment.transactionId}</p>}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Audit Log */}
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-4">Audit Log</h2>
                        {logs.length === 0 ? (
                            <p className="text-[#A0A0A0] text-sm">No logs found.</p>
                        ) : (
                            <div className="flex flex-col gap-3">
                                {logs.map((log) => (
                                    <div key={log.id} className="flex gap-3 text-sm">
                                        <div className="w-2 h-2 mt-1.5 rounded-full bg-[#60A5FA] shrink-0" />
                                        <div>
                                            <p className="font-medium text-white capitalize">{log.action?.replace("_", " ")}</p>
                                            <p className="text-xs text-[#A0A0A0]">{new Date(log.createdAt).toLocaleString()}</p>
                                            {log.details && <p className="text-xs text-[#A0A0A0] mt-0.5">{JSON.stringify(log.details).slice(0, 50)}…</p>}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
