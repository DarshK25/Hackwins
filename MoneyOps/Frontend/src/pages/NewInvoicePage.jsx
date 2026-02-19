import { useState, useEffect, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Plus, Trash, ArrowLeft, Loader2, UserPlus } from "lucide-react";
import { toast } from "sonner";

// ── Default item shape ────────────────────────────────────────────────────────
const BLANK_ITEM = { description: "", quantity: 1, rate: 0, gstRate: 18, isService: false };
const BLANK_CLIENT = { name: "", email: "", phone: "", company: "", gstin: "", address: "" };

export default function NewInvoicePage() {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [previewData, setPreviewData] = useState(null);
    const [clients, setClients] = useState([]);
    const [loadingClients, setLoadingClients] = useState(true);
    const [clientDialogOpen, setClientDialogOpen] = useState(false);
    const [savingClient, setSavingClient] = useState(false);
    const [newClientData, setNewClientData] = useState(BLANK_CLIENT);
    const [formData, setFormData] = useState({
        clientId: "",
        customerName: "",
        date: new Date().toISOString().split("T")[0],
        dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
        items: [{ ...BLANK_ITEM }],
    });

    useEffect(() => {
        fetchClients();
    }, []);

    // ── API ───────────────────────────────────────────────────────────────────

    const fetchClients = async () => {
        try {
            const res = await fetch("/api/clients");
            const data = await res.json();
            setClients(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error("Failed to fetch clients:", error);
            setClients([]);
        } finally {
            setLoadingClients(false);
        }
    };

    const handleCreateClient = async () => {
        if (!newClientData.name.trim()) {
            toast.error("Client name is required");
            return;
        }

        setSavingClient(true);
        try {
            const res = await fetch("/api/clients", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(newClientData),
            });

            const data = await res.json();
            if (!res.ok || !data.success) throw new Error(data.message || "Failed to create client");

            toast.success("Client created successfully");
            setClientDialogOpen(false);
            setNewClientData(BLANK_CLIENT);

            await fetchClients();
            setFormData((prev) => ({
                ...prev,
                clientId: data.client.id,
                customerName: data.client.name,
            }));
        } catch (error) {
            toast.error(error?.message || "Failed to create client");
        } finally {
            setSavingClient(false);
        }
    };

    // ── Item helpers ──────────────────────────────────────────────────────────

    const handleItemChange = (index, field, value) => {
        const newItems = [...formData.items];
        newItems[index] = { ...newItems[index], [field]: value };
        setFormData((prev) => ({ ...prev, items: newItems }));
        setPreviewData(null); // reset preview on any change
    };

    const addItem = () => {
        setFormData((prev) => ({
            ...prev,
            items: [...prev.items, { ...BLANK_ITEM }],
        }));
    };

    const removeItem = (index) => {
        setFormData((prev) => ({
            ...prev,
            items: prev.items.filter((_, i) => i !== index),
        }));
    };

    // ── Live calculation (memoised) ───────────────────────────────────────────

    const liveCalculation = useMemo(() => {
        let subtotal = 0;
        let totalGst = 0;

        formData.items.forEach((item) => {
            const itemAmount = item.isService ? item.rate : item.quantity * item.rate;
            const itemGst = (itemAmount * item.gstRate) / 100;
            subtotal += itemAmount;
            totalGst += itemGst;
        });

        return {
            subtotal: subtotal.toFixed(2),
            gstTotal: totalGst.toFixed(2),
            total: (subtotal + totalGst).toFixed(2),
        };
    }, [formData.items]);

    // ── Build line items payload ──────────────────────────────────────────────

    const buildLineItems = () =>
        formData.items.map((item) => {
            const itemAmount = item.isService ? item.rate : item.quantity * item.rate;
            return {
                description: item.description,
                quantity: item.isService ? 1 : item.quantity,
                rate: item.rate,
                gstRate: item.gstRate,
                isService: item.isService,
                amount: itemAmount,
                gstAmount: (itemAmount * item.gstRate) / 100,
                total: itemAmount + (itemAmount * item.gstRate) / 100,
            };
        });

    // ── Preview & Submit ──────────────────────────────────────────────────────

    const handlePreview = async () => {
        setLoading(true);
        try {
            const res = await fetch("/api/invoices/preview", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    items: buildLineItems(),
                    customerName: formData.customerName,
                    dueDate: formData.dueDate,
                    clientRequestId: Math.random().toString(),
                }),
            });

            const data = await res.json();
            if (!res.ok || !data.success) throw new Error(data.message || "Failed to preview");
            setPreviewData(data.preview);
        } catch (error) {
            toast.error(error?.message || "Preview failed");
        } finally {
            setLoading(false);
        }
    };

    const handleCreate = async () => {
        setLoading(true);
        try {
            const res = await fetch("/api/invoices", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    clientId: formData.clientId || undefined,
                    customerName: formData.customerName,
                    dueDate: new Date(formData.dueDate),
                    issueDate: new Date(formData.date),
                    items: buildLineItems(),
                    clientRequestId: Math.random().toString(),
                }),
            });

            const data = await res.json();
            if (!res.ok || !data.success) throw new Error(data.message || "Failed to create");

            toast.success(data.message || "Invoice created successfully");
            navigate("/invoices");
        } catch (error) {
            toast.error(error?.message || "Failed to create invoice");
        } finally {
            setLoading(false);
        }
    };

    // ── Render ────────────────────────────────────────────────────────────────

    return (
        <div className="space-y-6">
            {/* ── Page breadcrumb ──────────────────────────────────────────── */}
            <div>
                <Link
                    to="/invoices"
                    className="text-slate-500 hover:text-slate-900 flex items-center gap-1 mb-4 text-sm"
                >
                    <ArrowLeft className="h-4 w-4" /> Back to Invoices
                </Link>
                <h2 className="text-3xl font-bold tracking-tight">Create New Invoice</h2>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* ── Left column — inputs ──────────────────────────────────── */}
                <div className="space-y-6">
                    {/* Invoice Details */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Invoice Details</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {/* Customer Name */}
                            <div className="space-y-2">
                                <Label htmlFor="customerName">Customer Name *</Label>
                                <Input
                                    id="customerName"
                                    value={formData.customerName}
                                    onChange={(e) =>
                                        setFormData((prev) => ({ ...prev, customerName: e.target.value, clientId: "" }))
                                    }
                                    placeholder="Enter name or select an existing client below"
                                />
                            </div>

                            {/* Existing client select */}
                            <div className="space-y-1">
                                <p className="text-xs text-slate-400">
                                    Or select an existing client (saves full details):
                                </p>
                                <div className="flex gap-2">
                                    <Select
                                        value={formData.clientId}
                                        onValueChange={(value) => {
                                            const c = clients.find((cl) => cl.id === value);
                                            setFormData((prev) => ({
                                                ...prev,
                                                clientId: value,
                                                customerName: c?.name || "",
                                            }));
                                        }}
                                    >
                                        <SelectTrigger className="flex-1">
                                            <SelectValue
                                                placeholder={
                                                    loadingClients ? "Loading…" : "Select existing client (optional)"
                                                }
                                            />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {clients.map((client) => (
                                                <SelectItem key={client.id} value={client.id}>
                                                    {client.name}
                                                    {client.company ? ` (${client.company})` : ""}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                    <Button
                                        type="button"
                                        variant="outline"
                                        size="icon"
                                        onClick={() => setClientDialogOpen(true)}
                                        title="Add new client"
                                    >
                                        <UserPlus className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>

                            {/* Dates */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="invoiceDate">Invoice Date</Label>
                                    <Input
                                        id="invoiceDate"
                                        type="date"
                                        value={formData.date}
                                        onChange={(e) =>
                                            setFormData((prev) => ({ ...prev, date: e.target.value }))
                                        }
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="dueDate">Due Date</Label>
                                    <Input
                                        id="dueDate"
                                        type="date"
                                        value={formData.dueDate}
                                        onChange={(e) =>
                                            setFormData((prev) => ({ ...prev, dueDate: e.target.value }))
                                        }
                                    />
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Line Items */}
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <CardTitle>Items</CardTitle>
                            <Button variant="outline" size="sm" onClick={addItem}>
                                <Plus className="h-4 w-4 mr-2" /> Add Item
                            </Button>
                        </CardHeader>
                        <CardContent className="space-y-5">
                            {formData.items.map((item, index) => (
                                <div key={index} className="space-y-3 pb-4 border-b last:border-0 last:pb-0">
                                    {/* Service toggle */}
                                    <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={item.isService}
                                            onChange={(e) => handleItemChange(index, "isService", e.target.checked)}
                                            className="rounded"
                                        />
                                        Service (no quantity)
                                    </label>

                                    <div className="flex flex-wrap gap-3 items-end">
                                        {/* Description */}
                                        <div className="flex-1 min-w-0 space-y-1.5">
                                            <Label className="text-xs">
                                                {item.isService ? "Service Description" : "Item Description"}
                                            </Label>
                                            <Input
                                                value={item.description}
                                                onChange={(e) => handleItemChange(index, "description", e.target.value)}
                                                placeholder={
                                                    item.isService
                                                        ? "e.g., Web Development, Consulting"
                                                        : "e.g., Product name"
                                                }
                                            />
                                        </div>

                                        {/* Quantity (products only) */}
                                        {!item.isService && (
                                            <div className="w-20 space-y-1.5">
                                                <Label className="text-xs">Qty</Label>
                                                <Input
                                                    type="number"
                                                    min="1"
                                                    value={item.quantity}
                                                    onChange={(e) =>
                                                        handleItemChange(index, "quantity", Number(e.target.value))
                                                    }
                                                />
                                            </div>
                                        )}

                                        {/* Rate */}
                                        <div className="w-32 space-y-1.5">
                                            <Label className="text-xs">{item.isService ? "Amount" : "Rate"}</Label>
                                            <Input
                                                type="number"
                                                value={item.rate}
                                                onChange={(e) =>
                                                    handleItemChange(index, "rate", Number(e.target.value))
                                                }
                                                placeholder="0.00"
                                            />
                                        </div>

                                        {/* GST % */}
                                        <div className="w-24 space-y-1.5">
                                            <Label className="text-xs">GST %</Label>
                                            <Input
                                                type="number"
                                                value={item.gstRate}
                                                onChange={(e) =>
                                                    handleItemChange(index, "gstRate", Number(e.target.value))
                                                }
                                                placeholder="18"
                                            />
                                        </div>

                                        {/* Remove */}
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="text-red-500 hover:text-red-700"
                                            onClick={() => removeItem(index)}
                                        >
                                            <Trash className="h-4 w-4" />
                                        </Button>
                                    </div>

                                    {item.isService && (
                                        <p className="text-xs text-slate-400">
                                            💡 Service mode: Amount is the total price (no quantity needed)
                                        </p>
                                    )}
                                </div>
                            ))}
                        </CardContent>
                    </Card>

                    <Button
                        onClick={handlePreview}
                        disabled={loading}
                        variant="outline"
                        className="w-full"
                    >
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Preview Invoice
                    </Button>
                </div>

                {/* ── Right column — live calc + preview ───────────────────── */}
                <div className="space-y-6">
                    {/* Live Calculation */}
                    <Card className="bg-blue-50">
                        <CardHeader>
                            <CardTitle className="text-base">Live Calculation</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3 text-sm">
                            <div className="flex justify-between">
                                <span className="text-slate-500">Subtotal:</span>
                                <span className="font-medium">₹{liveCalculation.subtotal}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-500">GST Total:</span>
                                <span className="font-medium">₹{liveCalculation.gstTotal}</span>
                            </div>
                            <div className="flex justify-between font-bold text-lg border-t pt-3">
                                <span>Total Amount:</span>
                                <span className="text-blue-600">₹{liveCalculation.total}</span>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Preview Summary */}
                    {previewData ? (
                        <Card className="bg-slate-50">
                            <CardHeader>
                                <CardTitle className="text-base">Preview Summary</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-3 text-sm">
                                <div className="flex justify-between">
                                    <span>Subtotal:</span>
                                    <span>₹{previewData.subtotal?.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>CGST:</span>
                                    <span>₹{previewData.cgst?.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>SGST:</span>
                                    <span>₹{previewData.sgst?.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between font-bold text-lg border-t pt-3">
                                    <span>Total:</span>
                                    <span>₹{previewData.total?.toFixed(2)}</span>
                                </div>

                                {previewData.riskFlags?.length > 0 && (
                                    <div
                                        className="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-800 p-4 rounded"
                                        role="alert"
                                    >
                                        <p className="font-semibold mb-1">Attention Needed</p>
                                        <ul className="list-disc ml-4 space-y-1 text-sm">
                                            {previewData.riskFlags.map((flag, i) => (
                                                <li key={i}>{flag}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                <Button
                                    onClick={handleCreate}
                                    disabled={loading}
                                    className="w-full mt-2"
                                >
                                    {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Confirm & Create Invoice
                                </Button>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="flex items-center justify-center h-40 text-slate-400 border-2 border-dashed rounded-xl text-sm">
                            Fill details and click Preview to see summary
                        </div>
                    )}
                </div>
            </div>

            {/* ── Create Client Dialog ──────────────────────────────────────── */}
            <Dialog open={clientDialogOpen} onOpenChange={setClientDialogOpen}>
                <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>Create New Client</DialogTitle>
                        <DialogDescription>
                            Add a new client with full details. This will be saved to your client database.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                            <Label htmlFor="nc-name">Name *</Label>
                            <Input
                                id="nc-name"
                                value={newClientData.name}
                                onChange={(e) =>
                                    setNewClientData((p) => ({ ...p, name: e.target.value }))
                                }
                                placeholder="John Doe"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="nc-email">Email</Label>
                            <Input
                                id="nc-email"
                                type="email"
                                value={newClientData.email}
                                onChange={(e) =>
                                    setNewClientData((p) => ({ ...p, email: e.target.value }))
                                }
                                placeholder="john@example.com"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="nc-phone">Phone</Label>
                            <Input
                                id="nc-phone"
                                value={newClientData.phone}
                                onChange={(e) =>
                                    setNewClientData((p) => ({ ...p, phone: e.target.value }))
                                }
                                placeholder="+91 98765 43210"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="nc-company">Company</Label>
                            <Input
                                id="nc-company"
                                value={newClientData.company}
                                onChange={(e) =>
                                    setNewClientData((p) => ({ ...p, company: e.target.value }))
                                }
                                placeholder="Acme Corp"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="nc-gstin">GSTIN (Optional)</Label>
                            <Input
                                id="nc-gstin"
                                value={newClientData.gstin}
                                onChange={(e) =>
                                    setNewClientData((p) => ({
                                        ...p,
                                        gstin: e.target.value.toUpperCase(),
                                    }))
                                }
                                placeholder="22AAAAA0000A1Z5"
                                maxLength={15}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="nc-address">Address</Label>
                            <Textarea
                                id="nc-address"
                                value={newClientData.address}
                                onChange={(e) =>
                                    setNewClientData((p) => ({ ...p, address: e.target.value }))
                                }
                                placeholder="123 Main St, City, State"
                                rows={2}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setClientDialogOpen(false)}>
                            Cancel
                        </Button>
                        <Button
                            onClick={handleCreateClient}
                            disabled={savingClient}
                            className="bg-green-600 hover:bg-green-700"
                        >
                            {savingClient && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Create Client
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
