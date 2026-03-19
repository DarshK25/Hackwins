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
    Edit2,
    ArrowRight,
    Filter,
    Hash
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
import ClientDetailDialog from "@/components/ClientDetailDialog";
import { AnimatePresence } from "framer-motion";

const INITIAL_FORM = {
    name: "",
    email: "",
    phoneNumber: "",
    company: "",
    taxId: "",
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
    const [selectedClient, setSelectedClient] = useState(null);

    useEffect(() => {
        if (internalUserId && internalOrgId) {
            fetchClients();
        }
    }, [internalUserId, internalOrgId]);

    // LISTEN FOR VOICE ACTIONS (Bug 3 Refresh)
    useEffect(() => {
        const handleVoiceAction = () => {
            console.log("Refetching clients due to voice action");
            fetchClients();
        };
        window.addEventListener("voice:client-created", handleVoiceAction);
        return () => window.removeEventListener("voice:client-created", handleVoiceAction);
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
            setSelectedClient(null);
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

    const handleClientUpdate = (updated) => {
        setClients(prev => prev.map(c => (c.id === updated.id ? updated : c)));
        if (selectedClient?.id === updated.id) setSelectedClient(updated);
    };

    return (
        <div className="mo-page">
            <AnimatePresence>
                {selectedClient && (
                    <ClientDetailDialog 
                        client={selectedClient} 
                        onClose={() => setSelectedClient(null)} 
                        onUpdate={handleClientUpdate}
                        onDelete={handleDeleteClient}
                        internalUserId={internalUserId}
                        internalOrgId={internalOrgId}
                    />
                )}
            </AnimatePresence>

            <div className="flex justify-between items-center mb-2">
                <div>
                    <h1 className="mo-h1">Clients</h1>
                    <p className="mo-text-secondary">Manage your business relationships and leads</p>
                </div>
                <div className="flex gap-3">
                    <button className="mo-btn-secondary" onClick={fetchClients} disabled={loading}>
                        <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                    <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                        <DialogTrigger asChild>
                            <button className="mo-btn-primary flex items-center gap-2">
                                <Plus className="h-4 w-4" /> New Client
                            </button>
                        </DialogTrigger>
                        <DialogContent className="bg-[#1A1A1A] border-[#2A2A2A] text-white">
                            <DialogHeader>
                                <DialogTitle className="text-white">Add New Client</DialogTitle>
                                <DialogDescription className="text-[#A0A0A0]">
                                    Enter details for your new client.
                                </DialogDescription>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                                <div className="grid gap-2">
                                    <Label htmlFor="name" className="text-white">Name</Label>
                                    <input
                                        id="name"
                                        className="mo-input px-3 py-2"
                                        value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        placeholder="Full Name"
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="email" className="text-white">Email</Label>
                                    <input
                                        id="email"
                                        className="mo-input px-3 py-2"
                                        value={formData.email}
                                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                        placeholder="Email Address"
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="phone" className="text-white">Phone</Label>
                                    <input
                                        id="phone"
                                        className="mo-input px-3 py-2"
                                        value={formData.phoneNumber}
                                        onChange={(e) => setFormData({ ...formData, phoneNumber: e.target.value })}
                                        placeholder="Phone Number"
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label htmlFor="address" className="text-white">Address</Label>
                                    <Textarea
                                        id="address"
                                        className="mo-input"
                                        value={formData.address}
                                        onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                                        placeholder="Office Address"
                                    />
                                </div>
                            </div>
                            <DialogFooter>
                                <button className="mo-btn-secondary" onClick={() => setDialogOpen(false)}>Cancel</button>
                                <button className="mo-btn-primary flex items-center gap-2" onClick={handleCreateClient} disabled={saving}>
                                    {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                                    Create Client
                                </button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </div>
            </div>

            <div className="relative mb-6">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#A0A0A0]" />
                <input
                    className="mo-input w-full pl-10 pr-4 py-2"
                    placeholder="Search clients..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>

            {loading ? (
                <div className="flex justify-center p-20">
                    <Loader2 className="h-8 w-8 animate-spin mo-accent" />
                </div>
            ) : filteredClients.length === 0 ? (
                <div className="mo-card text-center py-20 flex flex-col items-center">
                    <Users className="h-12 w-12 text-[#2A2A2A] mb-4" />
                    <h3 className="mo-h2 mb-2">No clients found</h3>
                    <p className="mo-text-secondary">Add your first client to get started.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filteredClients.map((client) => (
                        <div 
                            key={client.id} 
                            className="mo-card flex flex-col justify-between cursor-pointer hover:border-[#4CBB17]"
                            onClick={() => setSelectedClient(client)}
                        >
                            <div>
                                <div className="flex justify-between items-start mb-4">
                                    <div className="h-10 w-10 rounded-full bg-[#4CBB1720] flex items-center justify-center">
                                        <Building className="h-5 w-5 mo-accent" />
                                    </div>
                                    <div className="mo-badge-success">{client.status || 'Active'}</div>
                                </div>
                                <h3 className="mo-h2 mb-1 truncate">{client.name}</h3>
                                <p className="mo-text-secondary mb-4 truncate">{client.email || 'No email'}</p>
                                
                                <div className="space-y-2">
                                    {client.phoneNumber && (
                                        <div className="flex items-center gap-2 text-xs text-[#A0A0A0]">
                                            <Phone className="h-3 w-3" /> {client.phoneNumber}
                                        </div>
                                    )}
                                    {(client.taxId || client.gstin) && (
                                        <div className="flex items-center gap-2 text-xs text-[#A0A0A0]">
                                            <Hash className="h-3 w-3" /> {client.taxId || client.gstin}
                                        </div>
                                    )}
                                </div>
                            </div>
                            
                            <div className="mt-6 pt-4 border-t mo-divider flex justify-between items-center">
                                <span className="text-xs font-bold mo-accent">View Details</span>
                                <Edit2 className="h-4 w-4 text-[#2A2A2A]" />
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
