import { useState, useEffect, useRef } from "react";
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
import { getRememberedTeamSecurityCode, rememberTeamSecurityCode } from "@/lib/teamSecurityCode";

const INITIAL_FORM = {
    name: "",
    email: "",
    phoneNumber: "",
    company: "",
    gstin: "",
    notes: "",
    teamActionCode: "",
    source: "MANUAL",
};

const CLIENT_FORM_PLACEHOLDERS = {
    name: "Client contact name",
    email: "name@company.com",
    phone: "Contact phone number",
    company: "Client company name",
    gstin: "22AAAAA0000A1Z5",
    notes: "Optional notes",
    teamActionCode: "Enter team security code",
};

const CLIENT_PREVIEW_EMPTY_STATE = {
    name: "Not added yet",
    email: "Not added yet",
    phone: "Not added yet",
    company: "Not added yet",
    gstin: "Not added yet",
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
    const [voiceDraftActive, setVoiceDraftActive] = useState(false);
    const touchedFieldsRef = useRef({});

    useEffect(() => {
        if (internalUserId && internalOrgId) {
            fetchClients();
        }
    }, [internalUserId, internalOrgId]);

    useEffect(() => {
        if (!internalOrgId) return;
        setFormData((prev) => ({
            ...prev,
            teamActionCode: getRememberedTeamSecurityCode(internalOrgId),
        }));
    }, [internalOrgId]);

    const markTouched = (field) => {
        touchedFieldsRef.current[field] = Date.now();
    };

    const canApplyVoice = (field) => {
        const lastTouched = touchedFieldsRef.current[field] || 0;
        return Date.now() - lastTouched > 2500;
    };

    const applyVoiceClientDraft = (eventDetail) => {
        const draft = eventDetail?.draft || {};
        if (!draft || typeof draft !== "object") return;
        setVoiceDraftActive(true);
        setDialogOpen(true);
        setFormData((prev) => {
            const next = { ...prev };
            const mapping = {
                name: "name",
                email: "email",
                phone: "phoneNumber",
                phoneNumber: "phoneNumber",
                company: "company",
                company_name: "company",
                gstin: "gstin",
                city: "notes",
                team_code: "teamActionCode",
            };
            Object.entries(mapping).forEach(([source, target]) => {
                const value = draft[source];
                if (value && canApplyVoice(target)) {
                    next[target] = value;
                }
            });
            return next;
        });
    };

    useEffect(() => {
        const handleVoiceAction = () => {
            console.log("Refetching clients due to voice action");
            fetchClients();
        };
        const storedDraft = sessionStorage.getItem("voice_client_draft");
        if (storedDraft) {
            try {
                applyVoiceClientDraft({ draft: JSON.parse(storedDraft) });
            } catch {}
            sessionStorage.removeItem("voice_client_draft");
        }
        const handleVoiceOpenForm = (event) => applyVoiceClientDraft(event.detail);
        const handleVoiceDraft = (event) => applyVoiceClientDraft(event.detail);
        window.addEventListener("voice:client-created", handleVoiceAction);
        window.addEventListener("voice:open-client-form", handleVoiceOpenForm);
        window.addEventListener("voice:client-draft-updated", handleVoiceDraft);
        return () => {
            window.removeEventListener("voice:client-created", handleVoiceAction);
            window.removeEventListener("voice:open-client-form", handleVoiceOpenForm);
            window.removeEventListener("voice:client-draft-updated", handleVoiceDraft);
        };
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
        if (!formData.teamActionCode?.trim()) {
            toast.error("Team security code is required");
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
            rememberTeamSecurityCode(internalOrgId, formData.teamActionCode);
            setDialogOpen(false);
            setFormData({
                ...INITIAL_FORM,
                teamActionCode: getRememberedTeamSecurityCode(internalOrgId),
            });
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
                        <DialogContent className="bg-[#1A1A1A] border-[#2A2A2A] text-white p-0 overflow-hidden sm:max-w-[720px]">
                            <DialogHeader className="border-b border-[#2A2A2A] px-6 py-5">
                                <DialogTitle className="text-white">Add New Client</DialogTitle>
                                <DialogDescription className="text-[#A0A0A0]">
                                    Enter details for your new client.
                                </DialogDescription>
                            </DialogHeader>
                            <div className="max-h-[calc(88vh-150px)] overflow-y-auto px-6 py-5">
                                <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_260px]">
                                    <div className="grid gap-4">
                                        <div className="grid gap-2">
                                            <Label htmlFor="name" className="text-white">Contact Name</Label>
                                            <input
                                                id="name"
                                                className="mo-input px-3 py-2"
                                                value={formData.name}
                                                onChange={(e) => { markTouched("name"); setFormData({ ...formData, name: e.target.value }); }}
                                                placeholder={CLIENT_FORM_PLACEHOLDERS.name}
                                            />
                                        </div>
                                        <div className="grid gap-2">
                                            <Label htmlFor="email" className="text-white">Email</Label>
                                            <input
                                                id="email"
                                                className="mo-input px-3 py-2"
                                                value={formData.email}
                                                onChange={(e) => { markTouched("email"); setFormData({ ...formData, email: e.target.value }); }}
                                                placeholder={CLIENT_FORM_PLACEHOLDERS.email}
                                            />
                                        </div>
                                        <div className="grid gap-2">
                                            <Label htmlFor="phone" className="text-white">Phone</Label>
                                            <input
                                                id="phone"
                                                className="mo-input px-3 py-2"
                                                value={formData.phoneNumber}
                                                onChange={(e) => { markTouched("phoneNumber"); setFormData({ ...formData, phoneNumber: e.target.value }); }}
                                                placeholder={CLIENT_FORM_PLACEHOLDERS.phone}
                                            />
                                        </div>
                                        <div className="grid gap-2">
                                            <Label htmlFor="company" className="text-white">Company</Label>
                                            <input
                                                id="company"
                                                className="mo-input px-3 py-2"
                                                value={formData.company}
                                                onChange={(e) => { markTouched("company"); setFormData({ ...formData, company: e.target.value }); }}
                                                placeholder={CLIENT_FORM_PLACEHOLDERS.company}
                                            />
                                        </div>
                                        <div className="grid gap-2">
                                            <Label htmlFor="gstin" className="text-white">GSTIN</Label>
                                            <input
                                                id="gstin"
                                                className="mo-input px-3 py-2"
                                                value={formData.gstin}
                                                onChange={(e) => { markTouched("gstin"); setFormData({ ...formData, gstin: e.target.value.toUpperCase() }); }}
                                                placeholder={CLIENT_FORM_PLACEHOLDERS.gstin}
                                                maxLength={15}
                                            />
                                        </div>
                                        <div className="grid gap-2">
                                            <Label htmlFor="notes" className="text-white">Notes</Label>
                                            <Textarea
                                                id="notes"
                                                className="mo-input min-h-[96px]"
                                                value={formData.notes}
                                                onChange={(e) => { markTouched("notes"); setFormData({ ...formData, notes: e.target.value }); }}
                                                placeholder={CLIENT_FORM_PLACEHOLDERS.notes}
                                            />
                                        </div>
                                        <div className="grid gap-2">
                                            <Label htmlFor="teamActionCode" className="text-white">Team Security Code</Label>
                                            <input
                                                id="teamActionCode"
                                                type="password"
                                                className="mo-input px-3 py-2"
                                                value={formData.teamActionCode}
                                                onChange={(e) => { markTouched("teamActionCode"); setFormData({ ...formData, teamActionCode: e.target.value }); }}
                                                placeholder={CLIENT_FORM_PLACEHOLDERS.teamActionCode}
                                            />
                                        </div>
                                    </div>
                                    <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] p-4 h-fit lg:sticky lg:top-0">
                                        <div className="flex items-center justify-between gap-3 mb-3">
                                            <p className="text-sm font-semibold text-white">Live Client Preview</p>
                                            {voiceDraftActive && <span className="text-[11px] font-medium text-[#4CBB17] whitespace-nowrap">Voice Sync Active</span>}
                                        </div>
                                        <div className="space-y-3 text-sm">
                                            <div className="min-w-0">
                                                <div className="text-[#A0A0A0] mb-1">Contact Name</div>
                                                <div className="text-white break-words">{formData.name || CLIENT_PREVIEW_EMPTY_STATE.name}</div>
                                            </div>
                                            <div className="min-w-0">
                                                <div className="text-[#A0A0A0] mb-1">Email</div>
                                                <div className="text-white break-all">{formData.email || CLIENT_PREVIEW_EMPTY_STATE.email}</div>
                                            </div>
                                            <div className="min-w-0">
                                                <div className="text-[#A0A0A0] mb-1">Phone</div>
                                                <div className="text-white break-words">{formData.phoneNumber || CLIENT_PREVIEW_EMPTY_STATE.phone}</div>
                                            </div>
                                            <div className="min-w-0">
                                                <div className="text-[#A0A0A0] mb-1">Company</div>
                                                <div className="text-white break-words">{formData.company || CLIENT_PREVIEW_EMPTY_STATE.company}</div>
                                            </div>
                                            <div className="min-w-0">
                                                <div className="text-[#A0A0A0] mb-1">GSTIN</div>
                                                <div className="text-white break-words">{formData.gstin || CLIENT_PREVIEW_EMPTY_STATE.gstin}</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <DialogFooter className="border-t border-[#2A2A2A] px-6 py-4 sm:justify-between">
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
