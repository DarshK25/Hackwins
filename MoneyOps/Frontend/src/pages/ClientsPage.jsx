import { useState, useEffect } from "react";
import { useAuth } from "@clerk/clerk-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
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
} from "lucide-react";
import { toast } from "sonner";

// ── Initial form state ────────────────────────────────────────────────────────
const INITIAL_FORM = {
    name: "",
    email: "",
    phoneNumber: "",
    company: "",
    taxId: "",
    address: "",
    notes: "",
    status: "ACTIVE",
};

export default function ClientsPage() {
    const { getToken, userId, orgId } = useAuth();
    const [clients, setClients] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [dialogOpen, setDialogOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const [formData, setFormData] = useState(INITIAL_FORM);

    const fetchClients = async () => {
        try {
            setLoading(true);
            const token = await getToken();
            const res = await fetch("/api/clients", {
                headers: {
                    Authorization: `Bearer ${token}`,
                    "X-User-Id": userId,
                    "X-Org-Id": orgId || "placeholder_org"
                }
            });
            if (!res.ok) throw new Error("Failed to fetch");
            const data = await res.json();
            setClients(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error("Fetch error:", err);
            toast.error("Failed to load clients");
            setClients([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (userId) {
            fetchClients();
        }
    }, [userId]);

    // Auto-refresh when a client is created via voice
    useEffect(() => {
        const handler = () => {
            fetchClients();
        };
        window.addEventListener("voice:client-created", handler);
        return () => window.removeEventListener("voice:client-created", handler);
    }, []);

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
                    Authorization: `Bearer ${token}`,
                    "X-User-Id": userId,
                    "X-Org-Id": orgId || "placeholder_org"
                },
                body: JSON.stringify(formData),
            });

            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.message || "Failed to create client");
            }

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

    // ── Derived state ───────────────────────────────────────────────────────────

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

    // ── Helpers ────────────────────────────────────────────────────────────────

    const updateForm = (field, value) =>
        setFormData((prev) => ({ ...prev, [field]: value }));

    // ── Render ──────────────────────────────────────────────────────────────────

    return (
        <div className="space-y-6">
            {/* ── Page Header ──────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight">Clients</h2>
                    <p className="text-muted-foreground text-sm mt-1">Manage your client relationships</p>
                </div>

                <div className="flex items-center gap-2">
                    {/* Refresh */}
                    <Button variant="outline" size="icon" onClick={fetchClients} disabled={loading}>
                        <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    </Button>

                    {/* Create dialog */}
                    <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                        <DialogTrigger asChild>
                            <Button className="bg-green-600 hover:bg-green-700">
                                <Plus className="h-4 w-4 mr-2" /> New Client
                            </Button>
                        </DialogTrigger>

                        <DialogContent className="sm:max-w-[500px] max-h-[90vh] overflow-y-auto">
                            <DialogHeader>
                                <DialogTitle>Create New Client</DialogTitle>
                                <DialogDescription>
                                    Add a new client to your database. Fill in the details below.
                                </DialogDescription>
                            </DialogHeader>

                            <div className="grid gap-4 py-4">
                                {/* Name */}
                                <div className="grid gap-2">
                                    <Label htmlFor="client-name">Name *</Label>
                                    <Input
                                        id="client-name"
                                        value={formData.name}
                                        onChange={(e) => updateForm("name", e.target.value)}
                                        placeholder="John Doe"
                                    />
                                </div>

                                {/* Email */}
                                <div className="grid gap-2">
                                    <Label htmlFor="client-email">Email</Label>
                                    <Input
                                        id="client-email"
                                        type="email"
                                        value={formData.email}
                                        onChange={(e) => updateForm("email", e.target.value)}
                                        placeholder="john@example.com"
                                    />
                                </div>

                                {/* Phone */}
                                <div className="grid gap-2">
                                    <Label htmlFor="client-phone">Phone</Label>
                                    <Input
                                        id="client-phone"
                                        type="tel"
                                        value={formData.phoneNumber}
                                        onChange={(e) => updateForm("phoneNumber", e.target.value)}
                                        placeholder="+91 98765 43210"
                                    />
                                </div>

                                {/* Company */}
                                <div className="grid gap-2">
                                    <Label htmlFor="client-company">Company</Label>
                                    <Input
                                        id="client-company"
                                        value={formData.company}
                                        onChange={(e) => updateForm("company", e.target.value)}
                                        placeholder="Acme Corp"
                                    />
                                </div>

                                {/* GSTIN */}
                                <div className="grid gap-2">
                                    <Label htmlFor="client-gstin">GST Number (GSTIN)</Label>
                                    <Input
                                        id="client-gstin"
                                        value={formData.taxId}
                                        onChange={(e) => updateForm("taxId", e.target.value.toUpperCase())}
                                        placeholder="22AAAAA0000A1Z5"
                                        maxLength={15}
                                    />
                                    <p className="text-xs text-muted-foreground">15-character GST Identification Number</p>
                                </div>

                                {/* Address */}
                                <div className="grid gap-2">
                                    <Label htmlFor="client-address">Address</Label>
                                    <Textarea
                                        id="client-address"
                                        value={formData.address}
                                        onChange={(e) => updateForm("address", e.target.value)}
                                        placeholder="123 Main St, City, State"
                                        rows={2}
                                    />
                                </div>

                                {/* Notes */}
                                <div className="grid gap-2">
                                    <Label htmlFor="client-notes">Notes</Label>
                                    <Textarea
                                        id="client-notes"
                                        value={formData.notes}
                                        onChange={(e) => updateForm("notes", e.target.value)}
                                        placeholder="Additional notes about the client"
                                        rows={2}
                                    />
                                </div>
                            </div>

                            <DialogFooter>
                                <Button variant="outline" onClick={() => setDialogOpen(false)}>
                                    Cancel
                                </Button>
                                <Button
                                    onClick={handleCreateClient}
                                    disabled={saving}
                                    className="bg-green-600 hover:bg-green-700"
                                >
                                    {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                    Create Client
                                </Button>
                            </DialogFooter>
                        </DialogContent>
                    </Dialog>
                </div>
            </div>

            {/* ── Stats Cards ───────────────────────────────────────────────────── */}
            <div className="grid gap-4 md:grid-cols-4">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Total Clients</CardTitle>
                        <Users className="h-4 w-4 text-muted-foreground/60" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">{stats.total}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Active</CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground/60" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold text-green-600">{stats.active}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">Total Revenue</CardTitle>
                        <DollarSign className="h-4 w-4 text-muted-foreground/60" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">₹{stats.totalRevenue.toLocaleString()}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Avg Lifetime Value
                        </CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground/60" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-3xl font-bold">
                            ₹{stats.avgLifetimeValue.toFixed(0)}
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* ── Search ───────────────────────────────────────────────────────── */}
            <div className="relative max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground/60" />
                <Input
                    placeholder="Search clients…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                />
            </div>

            {/* ── Client List ──────────────────────────────────────────────────── */}
            {loading ? (
                <div className="flex items-center justify-center h-64">
                    <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
                </div>
            ) : filteredClients.length === 0 ? (
                /* Empty state */
                <Card className="border-dashed">
                    <CardContent className="flex flex-col items-center justify-center py-16">
                        <Users className="h-16 w-16 text-slate-300 mb-4" />
                        <h3 className="text-lg font-semibold mb-2">
                            {searchQuery ? "No clients found" : "No clients yet"}
                        </h3>
                        <p className="text-muted-foreground mb-6 text-center max-w-sm text-sm">
                            {searchQuery
                                ? "Try adjusting your search query"
                                : "Add your first client to start managing relationships and invoices"}
                        </p>
                        {!searchQuery && (
                            <Button
                                onClick={() => setDialogOpen(true)}
                                className="bg-green-600 hover:bg-green-700"
                            >
                                <Plus className="h-4 w-4 mr-2" /> Add Your First Client
                            </Button>
                        )}
                    </CardContent>
                </Card>
            ) : (
                /* Client cards grid */
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {filteredClients.map((client) => (
                        <Card key={client.id} className="hover:shadow-md transition-shadow cursor-pointer">
                            <CardHeader className="pb-3">
                                <div className="flex items-start justify-between">
                                    <div className="flex-1 min-w-0">
                                        <CardTitle className="text-lg truncate">{client.name}</CardTitle>
                                        <Badge
                                            variant={client.status === "active" ? "success" : "secondary"}
                                            className="mt-2"
                                        >
                                            {client.status || "active"}
                                        </Badge>
                                    </div>
                                </div>
                            </CardHeader>

                            <CardContent>
                                <div className="space-y-2 text-sm">
                                    {client.email && (
                                        <div className="flex items-center gap-2 text-muted-foreground">
                                            <Mail className="h-3.5 w-3.5 flex-shrink-0" />
                                            <span className="truncate">{client.email}</span>
                                        </div>
                                    )}
                                    {client.phoneNumber && (
                                        <div className="flex items-center gap-2 text-muted-foreground">
                                            <Phone className="h-3.5 w-3.5 flex-shrink-0" />
                                            <span>{client.phoneNumber}</span>
                                        </div>
                                    )}
                                    {client.company && (
                                        <div className="flex items-center gap-2 text-muted-foreground">
                                            <Building className="h-3.5 w-3.5 flex-shrink-0" />
                                            <span className="truncate">{client.company}</span>
                                        </div>
                                    )}
                                    {client.taxId && (
                                        <div className="flex items-center gap-2">
                                            <Badge variant="secondary" className="font-mono text-xs">
                                                GST: {client.taxId}
                                            </Badge>
                                        </div>
                                    )}
                                    {client.totalRevenue > 0 && (
                                        <div className="pt-2 mt-2 border-t border-slate-100">
                                            <p className="text-xs text-slate-400">Total Revenue</p>
                                            <p className="font-semibold text-slate-800">
                                                ₹{client.totalRevenue.toLocaleString()}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
