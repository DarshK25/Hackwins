import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { toast } from "sonner";
import {
    FileText,
    Lock,
    Download,
    Trash2,
    Eye,
    Sparkles,
    Clock,
    AlertCircle,
    Loader2,
} from "lucide-react";
import { DocumentUpload } from "@/components/DocumentUpload";
import { cn } from "@/lib/utils";

// ── Fallback business ID ──────────────────────────────────────────────────────
const DEFAULT_BUSINESS_ID = 1;

export default function DocumentsPage() {
    const [loading, setLoading] = useState(true);
    const [businessId, setBusinessId] = useState(DEFAULT_BUSINESS_ID);
    const [sharedDocuments, setSharedDocuments] = useState([]);
    const [privateDocuments, setPrivateDocuments] = useState([]);

    useEffect(() => {
        initBusiness();
    }, []);

    // ── Init & Fetch ──────────────────────────────────────────────────────────

    async function initBusiness() {
        try {
            // Simulate/Real fetch for current business context
            // In a real app this might come from a context provider or auth hook
            const initRes = await fetch("/api/init").catch(() => null);
            if (initRes?.ok) {
                const initData = await initRes.json();
                const bId = initData.business?.id || DEFAULT_BUSINESS_ID;
                setBusinessId(bId);
                await fetchDocuments(bId);
            } else {
                // Fallback if API fails (dev mode without backend)
                await fetchDocuments(DEFAULT_BUSINESS_ID);
            }
        } catch {
            toast.error("Failed to load business context");
        } finally {
            setLoading(false);
        }
    }

    async function fetchDocuments(bId) {
        try {
            // Parallel fetch for shared + private
            const [sharedRes, privateRes] = await Promise.all([
                fetch(`/api/documents?businessId=${bId}&showPrivate=false`).catch(() => null),
                fetch(`/api/documents?businessId=${bId}&showPrivate=true`).catch(() => null),
            ]);

            const sharedData = sharedRes?.ok ? await sharedRes.json() : { documents: [] };
            const privateData = privateRes?.ok ? await privateRes.json() : { documents: [] };

            setSharedDocuments(sharedData.documents || []);
            setPrivateDocuments(privateData.documents || []);
        } catch (e) {
            console.error("Error fetching documents", e);
            toast.error("Failed to refresh documents");
        }
    }

    async function handleDelete(docId) {
        if (!window.confirm("Are you sure you want to delete this document?")) return;

        try {
            const res = await fetch(`/api/documents/${docId}`, { method: "DELETE" });
            if (!res.ok) throw new Error("Delete failed");

            toast.success("Document deleted");
            await fetchDocuments(businessId);
        } catch {
            toast.error("Failed to delete document");
        }
    }

    // ── Render Helpers ────────────────────────────────────────────────────────

    const renderDocumentCard = (doc) => (
        <div
            key={doc.id}
            className="flex items-center justify-between p-4 border rounded-lg hover:bg-slate-50 transition-colors group"
        >
            <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="h-10 w-10 rounded-lg bg-blue-50 flex items-center justify-center shrink-0 text-blue-600">
                    <FileText className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium truncate text-sm text-slate-900">
                            {doc.name}
                        </span>
                        {doc.isConfidential && (
                            <Badge variant="destructive" className="h-5 px-1.5 text-[10px]">
                                <Lock className="h-3 w-3 mr-1" /> Private
                            </Badge>
                        )}
                        {doc.analyzedAt && (
                            <Badge variant="secondary" className="h-5 px-1.5 text-[10px] bg-purple-100 text-purple-700 hover:bg-purple-200">
                                <Sparkles className="h-3 w-3 mr-1" /> AI Analyzed
                            </Badge>
                        )}
                    </div>

                    {doc.contentSummary && (
                        <p className="text-xs text-slate-500 mt-1 line-clamp-1">
                            {doc.contentSummary}
                        </p>
                    )}

                    <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-400">
                        <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(doc.uploadedAt).toLocaleDateString()}
                        </span>
                        {doc.category && (
                            <Badge variant="outline" className="h-5 px-1.5 text-[10px] fw-normal text-slate-500 border-slate-200">
                                {doc.category}
                            </Badge>
                        )}
                        {doc.detectedDeadlines?.length > 0 && (
                            <span className="flex items-center gap-1 text-orange-600 font-medium bg-orange-50 px-1.5 py-0.5 rounded">
                                <AlertCircle className="h-3 w-3" />
                                {doc.detectedDeadlines.length} deadline
                                {doc.detectedDeadlines.length > 1 ? "s" : ""}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-slate-400 hover:text-slate-700"
                    onClick={() => window.open(doc.url, "_blank")}
                    title="View"
                >
                    <Eye className="h-4 w-4" />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-slate-400 hover:text-slate-700"
                    onClick={() => {
                        const link = document.createElement("a");
                        link.href = doc.url;
                        link.download = doc.name;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                    }}
                    title="Download"
                >
                    <Download className="h-4 w-4" />
                </Button>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-slate-400 hover:text-red-600 hover:bg-red-50"
                    onClick={() => handleDelete(doc.id)}
                    title="Delete"
                >
                    <Trash2 className="h-4 w-4" />
                </Button>
            </div>
        </div>
    );

    // ── Loading Skeleton ──────────────────────────────────────────────────────

    if (loading) {
        return (
            <div className="p-8 space-y-8 animate-pulse max-w-5xl mx-auto">
                <div className="h-8 bg-slate-200 w-1/3 rounded"></div>
                <div className="grid md:grid-cols-2 gap-6">
                    <div className="h-64 bg-slate-100 rounded-lg"></div>
                    <div className="grid grid-cols-2 gap-4">
                        <div className="h-32 bg-slate-100 rounded-lg"></div>
                        <div className="h-32 bg-slate-100 rounded-lg"></div>
                    </div>
                </div>
            </div>
        );
    }

    // ── Main Render ───────────────────────────────────────────────────────────

    return (
        <div className="flex-1 space-y-6 p-6 max-w-7xl mx-auto">
            {/* Header */}
            <div>
                <h2 className="text-3xl font-bold tracking-tight">📂 Document Intelligence</h2>
                <p className="text-slate-500 mt-1">
                    AI-powered document management & analysis
                </p>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
                {/* Upload Column (takes 1/3 on large screens) */}
                <div className="lg:col-span-1">
                    <DocumentUpload
                        businessId={businessId}
                        onUploadComplete={() => fetchDocuments(businessId)}
                    />

                    {/* Mini Stats under upload */}
                    <div className="grid grid-cols-2 gap-4 mt-6">
                        <Card>
                            <CardHeader className="pb-2 p-4">
                                <CardTitle className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                                    Shared
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-4 pt-0">
                                <div className="text-2xl font-bold">{sharedDocuments.length}</div>
                                <p className="text-[10px] text-slate-400">Visible to team</p>
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader className="pb-2 p-4">
                                <CardTitle className="text-xs font-medium text-slate-500 uppercase tracking-wider flex items-center gap-1">
                                    <Lock className="h-3 w-3" /> Private
                                </CardTitle>
                            </CardHeader>
                            <CardContent className="p-4 pt-0">
                                <div className="text-2xl font-bold">{privateDocuments.length}</div>
                                <p className="text-[10px] text-slate-400">Only you can see</p>
                            </CardContent>
                        </Card>
                    </div>
                </div>

                {/* Documents List (takes 2/3 on large screens) */}
                <div className="lg:col-span-2">
                    <Tabs defaultValue="shared" className="w-full">
                        <div className="flex items-center justify-between mb-4">
                            <TabsList>
                                <TabsTrigger value="shared" className="gap-2">
                                    Shared Documents
                                    <Badge variant="secondary" className="px-1.5 h-5 min-w-[1.25rem] pointer-events-none">
                                        {sharedDocuments.length}
                                    </Badge>
                                </TabsTrigger>
                                <TabsTrigger value="private" className="gap-2">
                                    <Lock className="h-3 w-3" />
                                    Private Documents
                                    <Badge variant="secondary" className="px-1.5 h-5 min-w-[1.25rem] pointer-events-none">
                                        {privateDocuments.length}
                                    </Badge>
                                </TabsTrigger>
                            </TabsList>
                        </div>

                        <TabsContent value="shared" className="mt-0">
                            <Card>
                                <CardHeader className="pb-3 border-b">
                                    <CardTitle className="text-base font-semibold">Shared with Team</CardTitle>
                                </CardHeader>
                                <CardContent className="p-0">
                                    <ScrollArea className="h-[600px]">
                                        <div className="flex flex-col gap-2 p-4">
                                            {sharedDocuments.length === 0 ? (
                                                <EmptyState icon={FileText} message="No shared documents yet" subMessage="Upload documents to share with your team." />
                                            ) : (
                                                sharedDocuments.map(renderDocumentCard)
                                            )}
                                        </div>
                                    </ScrollArea>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="private" className="mt-0">
                            <Card>
                                <CardHeader className="pb-3 border-b bg-slate-50/50">
                                    <CardTitle className="text-base font-semibold flex items-center gap-2 text-slate-700">
                                        <Lock className="h-4 w-4 text-slate-400" />
                                        Private & Confidential
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="p-0">
                                    <ScrollArea className="h-[600px]">
                                        <div className="flex flex-col gap-2 p-4">
                                            {privateDocuments.length === 0 ? (
                                                <EmptyState icon={Lock} message="No private documents yet" subMessage="Mark documents as private to keep them confidential." />
                                            ) : (
                                                privateDocuments.map(renderDocumentCard)
                                            )}
                                        </div>
                                    </ScrollArea>
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </div>
            </div>
        </div>
    );
}

function EmptyState({ icon: Icon, message, subMessage }) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center text-slate-400 border-2 border-dashed border-slate-100 rounded-lg bg-slate-50/50">
            <div className="bg-white p-4 rounded-full shadow-sm mb-4">
                <Icon className="h-8 w-8 text-slate-300" />
            </div>
            <h3 className="text-sm font-medium text-slate-900">{message}</h3>
            <p className="text-sm mt-1 max-w-xs">{subMessage}</p>
        </div>
    );
}
