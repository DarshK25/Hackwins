import { useState, useEffect, useMemo, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
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
} from "@/components/ui/dialog";
import { Plus, Trash, ArrowLeft, Loader2, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { useAuth, useUser } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { getRememberedTeamSecurityCode, rememberTeamSecurityCode } from "@/lib/teamSecurityCode";

const BLANK_ITEM = { description: "", quantity: 1, rate: 0, gstPercent: 18, isService: false };
const BLANK_CLIENT = { name: "", email: "", phone: "", company: "", gstin: "", address: "", teamActionCode: "", source: "MANUAL" };

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

export default function NewInvoicePage() {
    const { getToken } = useAuth();
    const { user } = useUser();
    const { userId: internalUserId, orgId: internalOrgId } = useOnboardingStatus();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [previewData, setPreviewData] = useState(null);
    const [clients, setClients] = useState([]);
    const [loadingClients, setLoadingClients] = useState(true);
    const [clientDialogOpen, setClientDialogOpen] = useState(false);
    const [savingClient, setSavingClient] = useState(false);
    const [teamActionCode, setTeamActionCode] = useState("");
    const [voiceDraftActive, setVoiceDraftActive] = useState(false);
    const [newClientData, setNewClientData] = useState(BLANK_CLIENT);
    const touchedFieldsRef = useRef({});
    const [formData, setFormData] = useState({
        clientId: "",
        customerName: "",
        date: new Date().toISOString().split("T")[0],
        dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
        items: [{ ...BLANK_ITEM }],
    });

    useEffect(() => {
        if (internalUserId && internalOrgId) {
            fetchClients();
        }
    }, [internalUserId, internalOrgId]);

    const markTouched = (field) => {
        touchedFieldsRef.current[field] = Date.now();
    };

    const canApplyVoice = (field) => {
        const lastTouched = touchedFieldsRef.current[field] || 0;
        return Date.now() - lastTouched > 2500;
    };

    const applyVoiceInvoiceDraft = (eventDetail) => {
        const draft = eventDetail?.draft || {};
        if (!draft || typeof draft !== "object") return;
        setVoiceDraftActive(true);

        setFormData((prev) => {
            const next = { ...prev };
            const clientId = draft.client_id || draft.clientId;
            const clientName = draft.client_name || draft.customerName;
            if (clientId && canApplyVoice("clientId")) {
                next.clientId = clientId;
            }
            if (clientName && canApplyVoice("customerName")) {
                next.customerName = clientName;
                const matchedClient = clients.find((client) =>
                    (clientId && client.id === clientId)
                    || (client.name || "").toLowerCase() === clientName.toLowerCase()
                );
                if (matchedClient && canApplyVoice("clientId")) {
                    next.clientId = matchedClient.id;
                }
            }
            if ((draft.issue_date || draft.date) && canApplyVoice("date")) {
                next.date = draft.issue_date || draft.date;
            }
            if (draft.due_date && canApplyVoice("dueDate")) {
                next.dueDate = draft.due_date;
            }
            if (Array.isArray(draft.line_items) && draft.line_items.length && canApplyVoice("items")) {
                next.items = draft.line_items.map((item) => ({
                    description: item.description || "",
                    quantity: Number(item.quantity || 1),
                    rate: Number(item.unit_price || item.rate || 0),
                    gstPercent: Number(item.gst_percent || item.gstPercent || 18),
                    isService: String(item.type || "").toUpperCase() === "SERVICE"
                        || (!item.type && (!item.quantity || Number(item.quantity) <= 1)),
                }));
            }
            return next;
        });

        if (draft.team_code && canApplyVoice("teamActionCode")) {
            setTeamActionCode(draft.team_code);
        }
    };

    useEffect(() => {
        if (!internalOrgId) return;
        setTeamActionCode(getRememberedTeamSecurityCode(internalOrgId));
        setNewClientData((prev) => ({
            ...prev,
            teamActionCode: getRememberedTeamSecurityCode(internalOrgId),
        }));
    }, [internalOrgId]);

    useEffect(() => {
        const storedDraft = sessionStorage.getItem("voice_invoice_draft");
        if (storedDraft) {
            try {
                const parsedDraft = JSON.parse(storedDraft);
                applyVoiceInvoiceDraft(parsedDraft?.draft ? parsedDraft : { draft: parsedDraft });
            } catch {}
            sessionStorage.removeItem("voice_invoice_draft");
        }

        const handleVoiceDraft = (event) => applyVoiceInvoiceDraft(event.detail);
        const handleVoiceClientCreated = (event) => {
            const detail = event?.detail || {};
            fetchClients();
            setFormData((prev) => ({
                ...prev,
                customerName: detail.client_name || prev.customerName,
                clientId: detail.client_id || prev.clientId,
            }));
            if (detail.invoice_draft) {
                applyVoiceInvoiceDraft({ draft: detail.invoice_draft });
            }
        };
        window.addEventListener("voice:invoice-draft-updated", handleVoiceDraft);
        window.addEventListener("voice:client-created", handleVoiceClientCreated);
        return () => {
            window.removeEventListener("voice:invoice-draft-updated", handleVoiceDraft);
            window.removeEventListener("voice:client-created", handleVoiceClientCreated);
        };
    }, [clients]);

    useEffect(() => {
        if (!formData.customerName || formData.clientId || !clients.length) return;
        const matchedClient = clients.find((client) => (client.name || "").toLowerCase() === formData.customerName.toLowerCase());
        if (matchedClient) {
            setFormData((prev) => ({ ...prev, clientId: matchedClient.id }));
        }
    }, [clients, formData.customerName, formData.clientId]);

    const fetchClients = async () => {
        try {
            const token = await getToken();
            const res = await fetch("/api/clients", {
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId
                }
            });
            const data = await res.json();
            setClients(Array.isArray(data) ? data : []);
        } catch { setClients([]); }
        finally { setLoadingClients(false); }
    };

    const handleCreateClient = async () => {
        if (!newClientData.name.trim()) { toast.error("Client name is required"); return; }
        if (!newClientData.teamActionCode?.trim()) { toast.error("Team security code is required"); return; }
        setSavingClient(true);
        try {
            const token = await getToken();
            const res = await fetch("/api/clients", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId
                },
                body: JSON.stringify(newClientData),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.message || "Failed to create client");
            toast.success("Client created successfully");
            rememberTeamSecurityCode(internalOrgId, newClientData.teamActionCode);
            setClientDialogOpen(false);
            setNewClientData({ ...BLANK_CLIENT, teamActionCode: getRememberedTeamSecurityCode(internalOrgId) });
            await fetchClients();
            // Client API returns ClientDto directly
            setFormData((prev) => ({ ...prev, clientId: data.id, customerName: data.name }));
        } catch (error) {
            toast.error(error?.message || "Failed to create client");
        } finally { setSavingClient(false); }
    };

    const handleItemChange = (index, field, value) => {
        markTouched("items");
        const newItems = [...formData.items];
        newItems[index] = { ...newItems[index], [field]: value };
        setFormData((prev) => ({ ...prev, items: newItems }));
        setPreviewData(null);
    };

    const liveCalculation = useMemo(() => {
        let subtotal = 0;
        let totalGst = 0;
        formData.items.forEach((item) => {
            const amt = item.isService ? item.rate : (item.quantity || 1) * item.rate;
            subtotal += amt;
            totalGst += (amt * (item.gstPercent || 0)) / 100;
        });
        return { subtotal: subtotal.toFixed(2), gstTotal: totalGst.toFixed(2), total: (subtotal + totalGst).toFixed(2) };
    }, [formData.items]);

    const buildLineItems = () =>
        formData.items.map((item) => ({
            type: item.isService ? "SERVICE" : "PRODUCT",
            description: item.description,
            quantity: item.isService ? null : (item.quantity || 1),
            rate: item.rate,
            gstPercent: item.gstPercent || 0
        }));

    const previewSummary = previewData || {
        subtotal: parseFloat(liveCalculation.subtotal || "0"),
        cgst: parseFloat(liveCalculation.gstTotal || "0") / 2,
        sgst: parseFloat(liveCalculation.gstTotal || "0") / 2,
        total: parseFloat(liveCalculation.total || "0"),
        riskFlags: [],
    };

    const handlePreview = async () => {
        if (!formData.clientId) { toast.error("Please select or create a client first"); return; }
        setLoading(true);
        try {
            const token = await getToken();
            const payload = {
                clientId: formData.clientId,
                issueDate: formData.date,
                dueDate: formData.dueDate,
                items: buildLineItems()
            };
            const res = await fetch("/api/invoices/preview", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId
                },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.message || "Failed to preview");
            // Since backend is returning the DTO back for now, we simulate the breakdown
            const subtotal = parseFloat(liveCalculation.subtotal);
            const gst = parseFloat(liveCalculation.gstTotal);
            setPreviewData({
                subtotal,
                cgst: gst / 2,
                sgst: gst / 2,
                total: subtotal + gst,
                riskFlags: []
            });
        } catch (error) { toast.error(error?.message || "Preview failed"); }
        finally { setLoading(false); }
    };

    const handleCreate = async () => {
        if (!formData.clientId) { toast.error("Please select or create a client first"); return; }
        if (!teamActionCode.trim()) { toast.error("Team security code is required"); return; }
        setLoading(true);
        try {
            const token = await getToken();
            const payload = {
                clientId: formData.clientId,
                issueDate: formData.date,
                dueDate: formData.dueDate,
                items: buildLineItems(),
                currency: "INR",
                status: "DRAFT",
                teamActionCode,
                source: "MANUAL"
            };
            const res = await fetch("/api/invoices", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId
                },
                body: JSON.stringify(payload),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.message || "Failed to create invoice");
            toast.success("Invoice created successfully");
            rememberTeamSecurityCode(internalOrgId, teamActionCode);
            navigate("/invoices");
        } catch (error) { toast.error(error?.message || "Failed to create invoice"); }
        finally { setLoading(false); }
    };

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div>
                <Link to="/invoices" className="flex items-center gap-1.5 text-sm text-[#A0A0A0] hover:text-[#4CBB17] transition-colors mb-3">
                    <ArrowLeft className="h-4 w-4" /> Back to Invoices
                </Link>
                <h1 className="mo-h1">Create New Invoice</h1>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* ── Left ──────────────────────────────────────────────────── */}
                <div className="flex flex-col gap-5">
                    {/* Invoice Details */}
                    <div className="mo-card">
                        <h2 className="mo-h2 mb-4">Invoice Details</h2>
                        <div className="flex flex-col gap-4">
                            <div>
                                <label htmlFor="new-inv-customer" className="text-sm font-medium text-[#A0A0A0] block mb-1.5">Customer Name *</label>
                                <DarkInput
                                    id="new-inv-customer"
                                    value={formData.customerName}
                                    onChange={(e) => {
                                        markTouched("customerName");
                                        markTouched("clientId");
                                        setFormData((prev) => ({ ...prev, customerName: e.target.value, clientId: "" }));
                                    }}
                                    placeholder="Enter name or select an existing client below"
                                />
                            </div>
                            <div>
                                <p className="text-xs text-[#A0A0A0] mb-1.5">Or select an existing client:</p>
                                <div className="flex gap-2">
                                    <Select
                                        value={formData.clientId}
                                        onValueChange={(value) => {
                                            markTouched("clientId");
                                            markTouched("customerName");
                                            const c = clients.find((cl) => cl.id === value);
                                            setFormData((prev) => ({ ...prev, clientId: value, customerName: c?.name || "" }));
                                        }}
                                    >
                                        <SelectTrigger className="flex-1 bg-[#1A1A1A] border-[#2A2A2A] text-white">
                                            <SelectValue placeholder={loadingClients ? "Loading…" : "Select existing client (optional)"} />
                                        </SelectTrigger>
                                        <SelectContent className="bg-[#1A1A1A] border-[#2A2A2A]">
                                            {clients.map((client) => (
                                                <SelectItem key={client.id} value={client.id} className="text-white focus:bg-[#2A2A2A]">
                                                    {client.name}{client.company ? ` (${client.company})` : ""}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <button
                                        type="button"
                                        className="px-3 py-2 rounded-lg border border-[#2A2A2A] text-[#A0A0A0] hover:text-[#4CBB17] hover:border-[#4CBB17] transition-all"
                                        onClick={() => setClientDialogOpen(true)}
                                        title="Add new client"
                                    >
                                        <UserPlus className="h-4 w-4" />
                                    </button>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label htmlFor="new-inv-date" className="text-sm font-medium text-[#A0A0A0] block mb-1.5">Invoice Date</label>
                                    <DarkInput id="new-inv-date" type="date" value={formData.date} onChange={(e) => { markTouched("date"); setFormData((prev) => ({ ...prev, date: e.target.value })); }} />
                                </div>
                                <div>
                                    <label htmlFor="new-inv-duedate" className="text-sm font-medium text-[#A0A0A0] block mb-1.5">Due Date</label>
                                    <DarkInput id="new-inv-duedate" type="date" value={formData.dueDate} onChange={(e) => { markTouched("dueDate"); setFormData((prev) => ({ ...prev, dueDate: e.target.value })); }} />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Line Items */}
                    <div className="mo-card">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="mo-h2">Items</h2>
                            <button
                                className="mo-btn-secondary flex items-center gap-1.5 text-sm"
                                onClick={() => {
                                    markTouched("items");
                                    setFormData((prev) => ({ ...prev, items: [...prev.items, { ...BLANK_ITEM }] }));
                                }}
                            >
                                <Plus className="h-3.5 w-3.5" /> Add Item
                            </button>
                        </div>
                        <div className="flex flex-col gap-5">
                            {formData.items.map((item, index) => (
                                <div key={index} className="pb-5 border-b border-[#2A2A2A] last:border-0 last:pb-0 flex flex-col gap-3">
                                    <label className="flex items-center gap-2 text-xs text-[#A0A0A0] cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={item.isService}
                                            onChange={(e) => handleItemChange(index, "isService", e.target.checked)}
                                            className="rounded"
                                        />
                                        Service (no quantity)
                                    </label>
                                    <div className="flex flex-wrap gap-3 items-end">
                                        <div className="flex-1 min-w-0">
                                            <label className="text-xs text-[#A0A0A0] block mb-1">
                                                {item.isService ? "Service Description" : "Item Description"}
                                            </label>
                                            <DarkInput
                                                value={item.description}
                                                onChange={(e) => handleItemChange(index, "description", e.target.value)}
                                                placeholder={item.isService ? "e.g., Web Development" : "e.g., Product name"}
                                            />
                                        </div>
                                        {!item.isService && (
                                            <div className="w-20">
                                                <label className="text-xs text-[#A0A0A0] block mb-1">Qty</label>
                                                <DarkInput type="number" min="1" value={item.quantity} onChange={(e) => handleItemChange(index, "quantity", Number(e.target.value))} />
                                            </div>
                                        )}
                                        <div className="w-28">
                                            <label className="text-xs text-[#A0A0A0] block mb-1">{item.isService ? "Amount" : "Rate"}</label>
                                            <DarkInput type="number" value={item.rate} onChange={(e) => handleItemChange(index, "rate", Number(e.target.value))} placeholder="0.00" />
                                        </div>
                                        <div className="w-20">
                                            <label className="text-xs text-[#A0A0A0] block mb-1">GST %</label>
                                            <DarkInput type="number" value={item.gstPercent} onChange={(e) => handleItemChange(index, "gstPercent", Number(e.target.value))} placeholder="18" />
                                        </div>
                                        <button
                                            className="p-2 rounded-lg text-[#A0A0A0] hover:text-[#CD1C18] hover:bg-[#CD1C1820] transition-all mb-0.5"
                                            onClick={() => {
                                                markTouched("items");
                                                setFormData((prev) => ({ ...prev, items: prev.items.filter((_, i) => i !== index) }));
                                            }}
                                        >
                                            <Trash className="h-4 w-4" />
                                        </button>
                                    </div>
                                    {item.isService && (
                                        <p className="text-xs text-[#A0A0A0]">💡 Service mode: Amount is the total price (no quantity needed)</p>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={handlePreview}
                        disabled={loading}
                        className="mo-btn-secondary w-full flex items-center justify-center gap-2"
                    >
                        {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                        Refresh Backend Risk Check
                    </button>
                </div>

                {/* ── Right ─────────────────────────────────────────────────── */}
                <div className="flex flex-col gap-5">
                    {/* Live Calculation */}
                    <div className="mo-card border-[#4CBB1740]">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="mo-h2">Live Calculation</h2>
                            {voiceDraftActive && <span className="text-[11px] font-medium text-[#4CBB17]">Voice Sync Active</span>}
                        </div>
                        <div className="flex flex-col gap-2 text-sm">
                            <div className="flex justify-between">
                                <span className="text-[#A0A0A0]">Subtotal</span>
                                <span className="font-medium text-white">₹{liveCalculation.subtotal}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-[#A0A0A0]">GST Total</span>
                                <span className="font-medium text-white">₹{liveCalculation.gstTotal}</span>
                            </div>
                            <div className="flex justify-between font-bold text-lg border-t border-[#2A2A2A] pt-3 mt-1">
                                <span className="text-white">Total Amount</span>
                                <span className="text-[#4CBB17]">₹{liveCalculation.total}</span>
                            </div>
                        </div>
                    </div>

                    <div className="mo-card">
                        <div className="flex items-center justify-between mb-4 gap-4">
                            <h2 className="mo-h2">Live Preview</h2>
                            <span className="text-xs text-[#A0A0A0]">Voice patches update the draft without blocking manual edits</span>
                        </div>
                        <div className="flex flex-col gap-2 text-sm mb-4">
                            <div className="flex justify-between"><span className="text-[#A0A0A0]">Client</span><span>{formData.customerName || "Waiting for client"}</span></div>
                            <div className="flex justify-between"><span className="text-[#A0A0A0]">Issue Date</span><span>{formData.date || "—"}</span></div>
                            <div className="flex justify-between"><span className="text-[#A0A0A0]">Due Date</span><span>{formData.dueDate || "—"}</span></div>
                            <div className="flex justify-between"><span className="text-[#A0A0A0]">Subtotal</span><span>₹{previewSummary.subtotal?.toFixed(2)}</span></div>
                            <div className="flex justify-between"><span className="text-[#A0A0A0]">CGST</span><span>₹{previewSummary.cgst?.toFixed(2)}</span></div>
                            <div className="flex justify-between"><span className="text-[#A0A0A0]">SGST</span><span>₹{previewSummary.sgst?.toFixed(2)}</span></div>
                            <div className="flex justify-between font-bold text-lg border-t border-[#2A2A2A] pt-3 mt-1">
                                <span className="text-white">Total</span>
                                <span className="text-[#4CBB17]">₹{previewSummary.total?.toFixed(2)}</span>
                            </div>
                        </div>
                        {previewSummary.riskFlags?.length > 0 && (
                            <div className="p-4 bg-[#FFB30015] border border-[#FFB30040] rounded-xl mb-4">
                                <p className="font-semibold text-[#FFB300] mb-2 text-sm">Attention Needed</p>
                                <ul className="space-y-1 text-sm text-[#A0A0A0]">
                                    {previewSummary.riskFlags.map((flag, i) => <li key={i}>• {flag}</li>)}
                                </ul>
                            </div>
                        )}
                        <div className="space-y-2 mb-4">
                            <label className="text-sm font-medium text-[#A0A0A0] block">Team Security Code *</label>
                            <DarkInput
                                type="password"
                                value={teamActionCode}
                                onChange={(e) => { markTouched("teamActionCode"); setTeamActionCode(e.target.value); }}
                                placeholder="Enter team security code"
                            />
                        </div>
                        <button onClick={handleCreate} disabled={loading} className="mo-btn-primary w-full flex items-center justify-center gap-2">
                            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                            Confirm & Create Invoice
                        </button>
                    </div>
                </div>
            </div>

            {/* ── Create Client Dialog ──────────────────────────────────────── */}
            <Dialog open={clientDialogOpen} onOpenChange={setClientDialogOpen}>
                <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto bg-[#111111] border-[#2A2A2A]">
                    <DialogHeader>
                        <DialogTitle className="text-white">Create New Client</DialogTitle>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                        {[
                            { label: "Name *", id: "nc-name", field: "name", placeholder: "John Doe" },
                            { label: "Email", id: "nc-email", field: "email", type: "email", placeholder: "john@example.com" },
                            { label: "Phone", id: "nc-phone", field: "phone", placeholder: "+91 98765 43210" },
                            { label: "Company", id: "nc-company", field: "company", placeholder: "Acme Corp" },
                            { label: "GSTIN (Optional)", id: "nc-gstin", field: "gstin", placeholder: "22AAAAA0000A1Z5" },
                            { label: "Team Security Code *", id: "nc-team-code", field: "teamActionCode", type: "password", placeholder: "Enter team security code" },
                        ].map(({ label, id, field, type, placeholder }) => (
                            <div key={id}>
                                <label htmlFor={id} className="text-sm font-medium text-[#A0A0A0] block mb-1.5">{label}</label>
                                <DarkInput
                                    id={id}
                                    type={type || "text"}
                                    value={newClientData[field]}
                                    onChange={(e) => {
                                        markTouched(`newClient.${field}`);
                                        setNewClientData((p) => ({ ...p, [field]: field === "gstin" ? e.target.value.toUpperCase() : e.target.value }));
                                    }}
                                    placeholder={placeholder}
                                    maxLength={field === "gstin" ? 15 : undefined}
                                />
                            </div>
                        ))}
                        <div>
                            <label htmlFor="nc-address" className="text-sm font-medium text-[#A0A0A0] block mb-1.5">Address</label>
                            <textarea
                                id="nc-address"
                                value={newClientData.address}
                                onChange={(e) => {
                                    markTouched("newClient.address");
                                    setNewClientData((p) => ({ ...p, address: e.target.value }));
                                }}
                                placeholder="123 Main St, City, State"
                                rows={2}
                                style={{ ...inputStyle, resize: "vertical" }}
                            />
                        </div>
                    </div>
                    <div className="flex gap-3 justify-end">
                        <button className="mo-btn-secondary" onClick={() => setClientDialogOpen(false)}>Cancel</button>
                        <button className="mo-btn-primary flex items-center gap-2" onClick={handleCreateClient} disabled={savingClient}>
                            {savingClient && <Loader2 className="h-4 w-4 animate-spin" />}
                            Create Client
                        </button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}
