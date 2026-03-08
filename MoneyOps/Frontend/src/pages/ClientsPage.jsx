import { useState, useEffect } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Plus,
    Users,
    Loader2,
    Mail,
    Phone,
    Building,
    RefreshCw,
    Search,
    TrendingUp,
    DollarSign,
    MoreVertical,
    Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth, useUser } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const INITIAL_FORM = {
    name: "",
    email: "",
    phone: "",
    company: "",
    gstin: "",
    address: "",
    notes: "",
};

export default function ClientsPage() {
    const { getToken } = useAuth();
    const { user } = useUser();
    const { userId: internalUserId, orgId: internalOrgId } = useOnboardingStatus();
    const [clients, setClients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [dialogOpen, setDialogOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const [formData, setFormData] = useState(INITIAL_FORM);

    useEffect(() => {
        if (internalUserId && internalOrgId) {
            fetchClients();
        }
    }, [internalUserId, internalOrgId]);

    const fetchClients = async () => {
        try {
            setLoading(true);
            const token = await getToken();
            const res = await fetch("/api/clients", {
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId
                }
            });
            if (!res.ok) throw new Error("Failed to fetch");
            const data = await res.json();
            setClients(Array.isArray(data) ? data : []);
        } catch {
            toast.error("Failed to load clients");
            setClients([]);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateClient = async () => {
        if (!formData.name.trim()) {
            toast.error("Client name is required");
            return;
        }
        setSaving(true);
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
                body: JSON.stringify(formData),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.message || "Failed to create client");
            toast.success("Client created successfully");
            setDialogOpen(false);
            setFormData(INITIAL_FORM);
            fetchClients();
        } catch (error) {
            toast.error(error?.message || "Failed to create client");
        } finally {
            setSaving(false);
        }
    };

    const handleDeleteClient = async (client) => {
        const id = client.id || client._id;
        if (!window.confirm(`Are you sure you want to delete client "${client.name}"? This cannot be undone.`)) return;

        setSaving(true);
        try {
            const token = await getToken();
            const res = await fetch(`/api/clients/${id}`, {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId
                }
            });
            if (!res.ok) throw new Error("Failed to delete client");
            toast.success("Client deleted successfully");
            fetchClients();
        } catch (error) {
            toast.error(error.message);
        } finally {
            setSaving(false);
        }
    };

    const filteredClients = clients.filter(
        (client) =>
            !searchQuery ||
            client.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            client.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            client.company?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const stats = {
        total: clients.length,
        active: clients.filter((c) => c.status === "active").length,
        totalRevenue: clients.reduce((sum, c) => sum + (c.totalRevenue || 0), 0),
        avgLifetimeValue:
            clients.length > 0
                ? clients.reduce((sum, c) => sum + (c.lifetimeValue || 0), 0) / clients.length
                : 0,
    };

    const updateForm = (field, value) => setFormData((prev) => ({ ...prev, [field]: value }));

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                    <h1 className="mo-h1">Clients</h1>
                    <p className="mo-text-secondary mt-1">Manage your client relationships</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        className="mo-btn-secondary flex items-center gap-2"
                        onClick={fetchClients}
                        disabled={loading}
                    >
                        <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    </button>
                    <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                        <DialogTrigger asChild>
                            <button className="mo-btn-primary flex items-center gap-2">
                                <Plus className="h-4 w-4" /> New Client
                            </button>
                        </DialogTrigger>
                        <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto bg-[#111111] border-[#2A2A2A] text-white">
                            <DialogHeader>
                                <DialogTitle className="text-white">Create New Client</DialogTitle>
                                <DialogDescription className="text-[#A0A0A0]">
                                    Add a new client to your database.
                                </DialogDescription>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                {[
                                    { id: "client-name", label: "Name *", field: "name", placeholder: "John Doe" },
                                    { id: "client-email", label: "Email", field: "email", type: "email", placeholder: "john@example.com" },
                                    { id: "client-phone", label: "Phone", field: "phone", type: "tel", placeholder: "+91 98765 43210" },
                                    { id: "client-company", label: "Company", field: "company", placeholder: "Acme Corp" },
                                    { id: "client-gstin", label: "GST Number", field: "gstin", placeholder: "22AAAAA0000A1Z5" },
                                ].map(({ id, label, field, type, placeholder }) => (
                                    <div key={id} className="grid gap-2">
                                        <label htmlFor={id} className="text-sm font-medium text-[#A0A0A0]">{label}</label>
                                        <input
                                            id={id}
                                            type={type || "text"}
                                            value={formData[field]}
                                            onChange={(e) => updateForm(field, e.target.value)}
                                            placeholder={placeholder}
                                            className="px-3 py-2 rounded-lg text-sm text-white placeholder-[#A0A0A0] focus:outline-none focus:border-[#4CBB17] focus:ring-1 focus:ring-[#4CBB17]"
                                            style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                                        />
                                    </div>
                                ))}
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Address</label>
                                    <Textarea
                                        value={formData.address}
                                        onChange={(e) => updateForm("address", e.target.value)}
                                        placeholder="123 Main St, City, State"
                                        rows={2}
                                        className="bg-[#1A1A1A] border-[#2A2A2A] text-white placeholder:text-[#A0A0A0] focus:border-[#4CBB17] resize-none"
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Notes</label>
                                    <Textarea
                                        value={formData.notes}
                                        onChange={(e) => updateForm("notes", e.target.value)}
                                        placeholder="Additional notes about the client"
                                        rows={2}
                                        className="bg-[#1A1A1A] border-[#2A2A2A] text-white placeholder:text-[#A0A0A0] focus:border-[#4CBB17] resize-none"
                                    />
                                </div>
                            </div>
                            <DialogFooter>
                                <button
                                    className="mo-btn-secondary"
                                    onClick={() => setDialogOpen(false)}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleCreateClient}
                                    disabled={saving}
                                    className="mo-btn-primary flex items-center gap-2"
                                >
                                    {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                                    Create Client
                                </button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </div>
            </div>

            {/* ── Stats ───────────────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-4">
                <div className="mo-stat-card">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-[#A0A0A0]">Total Clients</p>
                        <Users className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-3xl font-bold text-white">{stats.total}</div>
                </div>
                <div className="mo-stat-card">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-[#A0A0A0]">Active</p>
                        <TrendingUp className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-3xl font-bold text-[#4CBB17]">{stats.active}</div>
                </div>
                <div className="mo-stat-card">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-[#A0A0A0]">Total Revenue</p>
                        <DollarSign className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-3xl font-bold text-white">₹{stats.totalRevenue.toLocaleString()}</div>
                </div>
                <div className="mo-stat-card">
                    <div className="flex items-center justify-between mb-2">
                        <p className="text-sm text-[#A0A0A0]">Avg Lifetime Value</p>
                        <TrendingUp className="h-4 w-4 text-[#A0A0A0]" />
                    </div>
                    <div className="text-3xl font-bold text-white">₹{stats.avgLifetimeValue.toFixed(0)}</div>
                </div>
            </div>

            {/* ── Search ──────────────────────────────────────────────────────── */}
            <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#A0A0A0]" />
                <input
                    placeholder="Search clients…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 rounded-lg text-sm text-white placeholder-[#A0A0A0] focus:outline-none focus:border-[#4CBB17] focus:ring-1 focus:ring-[#4CBB17]"
                    style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                />
            </div>

            {/* ── Client List ─────────────────────────────────────────────────── */}
            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
                </div>
            ) : filteredClients.length === 0 ? (
                <div className="mo-card flex flex-col items-center justify-center py-16 border-dashed">
                    <Users className="h-16 w-16 text-[#2A2A2A] mb-4" />
                    <h3 className="text-lg font-semibold text-white mb-2">
                        {searchQuery ? "No clients found" : "No clients yet"}
                    </h3>
                    <p className="text-[#A0A0A0] mb-6 text-center max-w-sm text-sm">
                        {searchQuery
                            ? "Try adjusting your search query"
                            : "Add your first client to start managing relationships and invoices"}
                    </p>
                    {!searchQuery && (
                        <button
                            onClick={() => setDialogOpen(true)}
                            className="mo-btn-primary flex items-center gap-2"
                        >
                            <Plus className="h-4 w-4" /> Add Your First Client
                        </button>
                    )}
                </div>
            ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {filteredClients.map((client) => (
                        <div key={client.id} className="mo-card cursor-pointer">
                            <div className="flex items-start justify-between mb-3">
                                <div>
                                    <h3 className="text-base font-semibold text-white truncate">{client.name}</h3>
                                    <span
                                        className={`mt-1 inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ${client.status === "active"
                                            ? "bg-[#4CBB1720] text-[#4CBB17] border border-[#4CBB1740]"
                                            : "bg-[#A0A0A020] text-[#A0A0A0] border border-[#A0A0A040]"
                                            }`}
                                    >
                                        {client.status || "active"}
                                    </span>
                                </div>
                                <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                        <button className="p-1 rounded-md hover:bg-[#2A2A2A] text-[#A0A0A0] hover:text-white transition-colors">
                                            <MoreVertical className="h-4 w-4" />
                                        </button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end" className="bg-[#1A1A1A] border-[#2A2A2A]">
                                        <DropdownMenuItem
                                            onClick={() => handleDeleteClient(client)}
                                            className="text-red-500 hover:bg-[#CD1C1820] cursor-pointer"
                                        >
                                            <Trash2 className="h-4 w-4 mr-2" /> Delete
                                        </DropdownMenuItem>
                                    </DropdownMenuContent>
                                </DropdownMenu>
                            </div>
                            <div className="space-y-2 text-sm">
                                {client.email && (
                                    <div className="flex items-center gap-2 text-[#A0A0A0]">
                                        <Mail className="h-3.5 w-3.5 flex-shrink-0" />
                                        <span className="truncate">{client.email}</span>
                                    </div>
                                )}
                                {client.phone && (
                                    <div className="flex items-center gap-2 text-[#A0A0A0]">
                                        <Phone className="h-3.5 w-3.5 flex-shrink-0" />
                                        <span>{client.phone}</span>
                                    </div>
                                )}
                                {client.company && (
                                    <div className="flex items-center gap-2 text-[#A0A0A0]">
                                        <Building className="h-3.5 w-3.5 flex-shrink-0" />
                                        <span className="truncate">{client.company}</span>
                                    </div>
                                )}
                                {client.gstin && (
                                    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono bg-[#1A1A1A] text-[#A0A0A0] border border-[#2A2A2A]">
                                        GST: {client.gstin}
                                    </span>
                                )}
                                {client.totalRevenue > 0 && (
                                    <div className="pt-3 mt-2 border-t border-[#2A2A2A]">
                                        <p className="text-xs text-[#A0A0A0]">Total Revenue</p>
                                        <p className="font-semibold text-white">
                                            ₹{client.totalRevenue.toLocaleString()}
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
