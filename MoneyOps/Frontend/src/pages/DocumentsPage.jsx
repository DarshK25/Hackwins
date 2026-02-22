import { useEffect, useState } from "react";
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

const DEFAULT_BUSINESS_ID = 1;

export default function DocumentsPage() {
    const [loading, setLoading] = useState(true);
    const [businessId, setBusinessId] = useState(DEFAULT_BUSINESS_ID);
    const [sharedDocuments, setSharedDocuments] = useState([]);
    const [privateDocuments, setPrivateDocuments] = useState([]);

    useEffect(() => {
        initBusiness();
    }, []);

    async function initBusiness() {
        try {
            const initRes = await fetch("/api/init").catch(() => null);
            if (initRes?.ok) {
                const initData = await initRes.json();
                const bId = initData.business?.id || DEFAULT_BUSINESS_ID;
                setBusinessId(bId);
                await fetchDocuments(bId);
            } else {
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

    const renderDocumentCard = (doc) => (
        <div
            key={doc.id}
            className="flex items-center justify-between p-4 rounded-xl border border-[#2A2A2A] bg-[#111111] hover:border-[#3A3A3A] transition-colors group"
        >
            <div className="flex items-center gap-4 flex-1 min-w-0">
                <div className="h-10 w-10 rounded-xl bg-[#4CBB1715] border border-[#4CBB1730] flex items-center justify-center shrink-0">
                    <FileText className="h-5 w-5 text-[#4CBB17]" />
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-sm text-white truncate">{doc.name}</span>
                        {doc.isConfidential && (
                            <span className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-md bg-[#CD1C1820] text-[#CD1C18] border border-[#CD1C1840]">
                                <Lock className="h-3 w-3" /> Private
                            </span>
                        )}
                        {doc.analyzedAt && (
                            <span className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-md bg-[#A855F720] text-[#C084FC] border border-[#A855F740]">
                                <Sparkles className="h-3 w-3" /> AI Analyzed
                            </span>
                        )}
                    </div>
                    {doc.contentSummary && (
                        <p className="text-xs text-[#A0A0A0] mt-0.5 line-clamp-1">{doc.contentSummary}</p>
                    )}
                    <div className="flex items-center gap-3 mt-1.5 text-xs text-[#A0A0A0]">
                        <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(doc.uploadedAt).toLocaleDateString()}
                        </span>
                        {doc.category && (
                            <span className="px-1.5 py-0.5 rounded bg-[#2A2A2A] text-xs">{doc.category}</span>
                        )}
                        {doc.detectedDeadlines?.length > 0 && (
                            <span className="flex items-center gap-1 text-[#FFB300] font-medium">
                                <AlertCircle className="h-3 w-3" />
                                {doc.detectedDeadlines.length} deadline{doc.detectedDeadlines.length > 1 ? "s" : ""}
                            </span>
                        )}
                    </div>
                </div>
            </div>
            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-4">
                <button
                    className="p-2 rounded-lg text-[#A0A0A0] hover:text-white hover:bg-[#2A2A2A] transition-all"
                    onClick={() => window.open(doc.url, "_blank")}
                    title="View"
                >
                    <Eye className="h-4 w-4" />
                </button>
                <button
                    className="p-2 rounded-lg text-[#A0A0A0] hover:text-white hover:bg-[#2A2A2A] transition-all"
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
                </button>
                <button
                    className="p-2 rounded-lg text-[#A0A0A0] hover:text-[#CD1C18] hover:bg-[#CD1C1820] transition-all"
                    onClick={() => handleDelete(doc.id)}
                    title="Delete"
                >
                    <Trash2 className="h-4 w-4" />
                </button>
            </div>
        </div>
    );

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            {/* ── Header ──────────────────────────────────────────────────────── */}
            <div>
                <h1 className="mo-h1">Document Intelligence</h1>
                <p className="mo-text-secondary mt-1">AI-powered document management & analysis</p>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
                {/* Upload Column */}
                <div className="lg:col-span-1 flex flex-col gap-4">
                    <DocumentUpload
                        businessId={businessId}
                        onUploadComplete={() => fetchDocuments(businessId)}
                    />
                    {/* Mini Stats */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="mo-stat-card !py-4">
                            <p className="text-[10px] font-semibold uppercase tracking-widest text-[#A0A0A0] mb-2">
                                Shared
                            </p>
                            <div className="text-2xl font-bold text-white">{sharedDocuments.length}</div>
                            <p className="text-[10px] text-[#A0A0A0] mt-1">Visible to team</p>
                        </div>
                        <div className="mo-stat-card !py-4">
                            <p className="text-[10px] font-semibold uppercase tracking-widest text-[#A0A0A0] mb-2 flex items-center gap-1">
                                <Lock className="h-3 w-3" /> Private
                            </p>
                            <div className="text-2xl font-bold text-white">{privateDocuments.length}</div>
                            <p className="text-[10px] text-[#A0A0A0] mt-1">Only you can see</p>
                        </div>
                    </div>
                </div>

                {/* Documents List */}
                <div className="lg:col-span-2">
                    <Tabs defaultValue="shared" className="w-full">
                        <TabsList className="bg-[#1A1A1A] border border-[#2A2A2A] h-auto p-1 rounded-xl w-fit flex gap-1 mb-4">
                            <TabsTrigger
                                value="shared"
                                className="px-4 py-2 rounded-lg text-sm font-medium text-[#A0A0A0] data-[state=active]:bg-[#4CBB17] data-[state=active]:text-black transition-all flex items-center gap-2"
                            >
                                <FileText className="h-3.5 w-3.5" />
                                Shared
                                <span className="ml-1 text-xs bg-black/20 px-1.5 py-0.5 rounded-full">
                                    {sharedDocuments.length}
                                </span>
                            </TabsTrigger>
                            <TabsTrigger
                                value="private"
                                className="px-4 py-2 rounded-lg text-sm font-medium text-[#A0A0A0] data-[state=active]:bg-[#4CBB17] data-[state=active]:text-black transition-all flex items-center gap-2"
                            >
                                <Lock className="h-3.5 w-3.5" />
                                Private
                                <span className="ml-1 text-xs bg-black/20 px-1.5 py-0.5 rounded-full">
                                    {privateDocuments.length}
                                </span>
                            </TabsTrigger>
                        </TabsList>

                        <TabsContent value="shared" className="mt-0">
                            <div className="mo-card">
                                <h2 className="mo-h2 mb-4">Shared with Team</h2>
                                <ScrollArea className="h-[520px] pr-1">
                                    <div className="flex flex-col gap-2">
                                        {sharedDocuments.length === 0 ? (
                                            <DocEmptyState icon={FileText} message="No shared documents yet" subMessage="Upload documents to share with your team." />
                                        ) : (
                                            sharedDocuments.map(renderDocumentCard)
                                        )}
                                    </div>
                                </ScrollArea>
                            </div>
                        </TabsContent>

                        <TabsContent value="private" className="mt-0">
                            <div className="mo-card">
                                <div className="flex items-center gap-2 mb-4">
                                    <Lock className="h-4 w-4 text-[#A0A0A0]" />
                                    <h2 className="mo-h2">Private & Confidential</h2>
                                </div>
                                <ScrollArea className="h-[520px] pr-1">
                                    <div className="flex flex-col gap-2">
                                        {privateDocuments.length === 0 ? (
                                            <DocEmptyState icon={Lock} message="No private documents yet" subMessage="Mark documents as private to keep them confidential." />
                                        ) : (
                                            privateDocuments.map(renderDocumentCard)
                                        )}
                                    </div>
                                </ScrollArea>
                            </div>
                        </TabsContent>
                    </Tabs>
                </div>
            </div>
        </div>
    );
}

function DocEmptyState({ icon: Icon, message, subMessage }) {
    return (
        <div className="flex flex-col items-center justify-center py-16 text-center border-2 border-dashed border-[#2A2A2A] rounded-xl">
            <div className="p-4 rounded-full bg-[#1A1A1A] mb-4">
                <Icon className="h-8 w-8 text-[#2A2A2A]" />
            </div>
            <h3 className="text-sm font-semibold text-white">{message}</h3>
            <p className="text-sm text-[#A0A0A0] mt-1 max-w-xs">{subMessage}</p>
        </div>
    );
}
