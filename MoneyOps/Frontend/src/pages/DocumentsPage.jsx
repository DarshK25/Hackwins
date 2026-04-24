import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth, useUser } from "@clerk/clerk-react";
import {
    Download,
    FileText,
    Filter,
    Link2,
    Loader2,
    RefreshCw,
    Trash2,
    Upload,
} from "lucide-react";
import { toast } from "sonner";
import { Progress } from "@/components/ui/progress";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";

const PAGE_SIZE = 20;

const TYPE_OPTIONS = [
    { value: "ALL", label: "All Types" },
    { value: "INVOICE", label: "Invoice" },
    { value: "CLIENT", label: "Client" },
    { value: "CONTRACT", label: "Contract" },
    { value: "FINANCIAL", label: "Financial" },
    { value: "LEGAL", label: "Legal" },
    { value: "BANK_STATEMENT", label: "Bank Statement" },
    { value: "OTHER", label: "Other" },
];

const ENTITY_OPTIONS = [
    { value: "", label: "Not linked" },
    { value: "INVOICE", label: "Invoice" },
    { value: "CLIENT", label: "Client" },
];

function formatFileSize(value) {
    const size = Number(value || 0);
    if (size >= 1024 * 1024) {
        return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    }
    if (size >= 1024) {
        return `${(size / 1024).toFixed(1)} KB`;
    }
    return `${size} B`;
}

function formatDate(value) {
    if (!value) {
        return "--";
    }

    return new Date(value).toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

async function parseApiResponse(response, fallbackMessage) {
    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
        const payload = await response.json().catch(() => null);
        return payload?.message || payload?.error || payload?.data?.message || fallbackMessage;
    }

    const text = await response.text().catch(() => "");
    return text || fallbackMessage;
}

function emptyUploadState() {
    return {
        name: "",
        type: "OTHER",
        category: "",
        linkedEntityType: "",
        linkedEntityId: "",
        contentSummary: "",
        isConfidential: false,
    };
}

export default function DocumentsPage() {
    const navigate = useNavigate();
    const { getToken } = useAuth();
    const { user } = useUser();
    const { loading: onboardingLoading, userId, orgId } = useOnboardingStatus();

    const [documents, setDocuments] = useState([]);
    const [pageNumber, setPageNumber] = useState(0);
    const [totalPages, setTotalPages] = useState(0);
    const [totalElements, setTotalElements] = useState(0);
    const [loading, setLoading] = useState(true);
    const [filterType, setFilterType] = useState("ALL");
    const [selectedFile, setSelectedFile] = useState(null);
    const [fileInputKey, setFileInputKey] = useState(0);
    const [uploadForm, setUploadForm] = useState(emptyUploadState());
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [deletingDocumentId, setDeletingDocumentId] = useState(null);
    const [downloadingDocumentId, setDownloadingDocumentId] = useState(null);

    const hasContext = useMemo(() => Boolean(orgId && (userId || user?.id)), [orgId, userId, user?.id]);

    useEffect(() => {
        if (!onboardingLoading && hasContext) {
            fetchDocuments(0, filterType);
        }
    }, [filterType, hasContext, onboardingLoading]);

    async function buildHeaders(extra = {}) {
        const token = await getToken();
        return {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(userId || user?.id ? { "X-User-Id": userId || user?.id } : {}),
            ...(orgId ? { "X-Org-Id": orgId } : {}),
            ...extra,
        };
    }

    async function fetchDocuments(page = pageNumber, type = filterType) {
        if (!orgId) {
            setDocuments([]);
            setLoading(false);
            return;
        }

        try {
            setLoading(true);

            const headers = await buildHeaders();
            const query = new URLSearchParams({
                orgId,
                page: String(page),
                size: String(PAGE_SIZE),
            });

            if (type && type !== "ALL") {
                query.set("type", type);
            }

            const response = await fetch(`/api/documents?${query.toString()}`, { headers });
            if (!response.ok) {
                throw new Error(await parseApiResponse(response, "Failed to load documents"));
            }

            const payload = await response.json();
            const data = payload?.data || {};
            setDocuments(data.content || []);
            setPageNumber(data.pageNumber || 0);
            setTotalPages(data.totalPages || 0);
            setTotalElements(data.totalElements || 0);
        } catch (error) {
            console.error("Failed to load documents", error);
            toast.error(error.message || "Failed to load documents");
            setDocuments([]);
            setPageNumber(0);
            setTotalPages(0);
            setTotalElements(0);
        } finally {
            setLoading(false);
        }
    }

    function updateUploadField(field, value) {
        setUploadForm((current) => ({ ...current, [field]: value }));
    }

    function handleFileSelection(event) {
        const file = event.target.files?.[0] || null;
        setSelectedFile(file);

        if (!file) {
            return;
        }

        setUploadForm((current) => ({
            ...current,
            name: current.name || file.name,
        }));
    }

    function handleLinkedEntityNavigation(doc) {
        if (!doc.linkedEntityType || !doc.linkedEntityId) {
            return;
        }

        if (doc.linkedEntityType === "INVOICE") {
            navigate(`/invoices/${doc.linkedEntityId}`);
            return;
        }

        if (doc.linkedEntityType === "CLIENT") {
            navigate(`/clients?clientId=${encodeURIComponent(doc.linkedEntityId)}`);
        }
    }

    async function handleUpload() {
        if (!selectedFile) {
            toast.error("Choose a file to upload");
            return;
        }

        if (!orgId) {
            toast.error("Organization context is missing");
            return;
        }

        try {
            setUploading(true);
            setUploadProgress(0);

            const metadata = {
                orgId,
                name: uploadForm.name || selectedFile.name,
                type: uploadForm.type,
                category: uploadForm.category || null,
                linkedEntityType: uploadForm.linkedEntityType || null,
                linkedEntityId: uploadForm.linkedEntityId || null,
                contentSummary: uploadForm.contentSummary || null,
                isConfidential: uploadForm.isConfidential,
            };

            const formData = new FormData();
            formData.append("file", selectedFile);
            formData.append("metadata", new Blob([JSON.stringify(metadata)], { type: "application/json" }));

            const headers = await buildHeaders();

            await new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.open("POST", "/api/documents/upload");

                Object.entries(headers).forEach(([key, value]) => {
                    xhr.setRequestHeader(key, value);
                });

                xhr.upload.onprogress = (event) => {
                    if (event.lengthComputable) {
                        setUploadProgress(Math.round((event.loaded / event.total) * 100));
                    }
                };

                xhr.onload = async () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        setSelectedFile(null);
                        setFileInputKey((current) => current + 1);
                        setUploadForm(emptyUploadState());
                        setUploadProgress(100);
                        toast.success("Document uploaded successfully");
                        await fetchDocuments(0, filterType);
                        resolve();
                        return;
                    }

                    try {
                        const payload = JSON.parse(xhr.responseText || "{}");
                        reject(new Error(payload?.message || "Failed to upload document"));
                    } catch {
                        reject(new Error("Failed to upload document"));
                    }
                };

                xhr.onerror = () => reject(new Error("Failed to upload document"));
                xhr.send(formData);
            });
        } catch (error) {
            console.error("Failed to upload document", error);
            toast.error(error.message || "Failed to upload document");
        } finally {
            window.setTimeout(() => {
                setUploading(false);
                setUploadProgress(0);
            }, 500);
        }
    }

    async function handleDownload(doc) {
        if (!orgId) {
            toast.error("Organization context is missing");
            return;
        }

        try {
            setDownloadingDocumentId(doc.id);

            const headers = await buildHeaders();
            const response = await fetch(
                `/api/documents/${doc.id}/download?orgId=${encodeURIComponent(orgId)}`,
                { headers }
            );

            if (!response.ok) {
                throw new Error(await parseApiResponse(response, "Failed to get download URL"));
            }

            const payload = await response.json();
            const downloadUrl = payload?.data?.downloadUrl;
            if (!downloadUrl) {
                throw new Error("Download URL not available");
            }

            const link = window.document.createElement("a");
            link.href = downloadUrl;
            link.target = "_blank";
            link.rel = "noreferrer";
            link.download = doc.name || "document";
            window.document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            console.error("Failed to download document", error);
            toast.error(error.message || "Failed to download document");
        } finally {
            setDownloadingDocumentId(null);
        }
    }

    async function handleDelete(documentId) {
        if (!orgId) {
            toast.error("Organization context is missing");
            return;
        }

        if (!window.confirm("Delete this document? This will soft-delete it from the list.")) {
            return;
        }

        try {
            setDeletingDocumentId(documentId);

            const headers = await buildHeaders();
            const response = await fetch(`/api/documents/${documentId}?orgId=${encodeURIComponent(orgId)}`, {
                method: "DELETE",
                headers,
            });

            if (!response.ok) {
                throw new Error(await parseApiResponse(response, "Failed to delete document"));
            }

            toast.success("Document deleted");

            const nextPage = documents.length === 1 && pageNumber > 0 ? pageNumber - 1 : pageNumber;
            await fetchDocuments(nextPage, filterType);
        } catch (error) {
            console.error("Failed to delete document", error);
            toast.error(error.message || "Failed to delete document");
        } finally {
            setDeletingDocumentId(null);
        }
    }

    const showingFrom = totalElements === 0 ? 0 : pageNumber * PAGE_SIZE + 1;
    const showingTo = Math.min(totalElements, (pageNumber + 1) * PAGE_SIZE);

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="mo-h1">Documents</h1>
                    <p className="mo-text-secondary mt-1">
                        Upload, organize, download, and link documents to invoices and clients.
                    </p>
                </div>

                <button
                    onClick={() => fetchDocuments(pageNumber, filterType)}
                    className="mo-btn-secondary flex items-center gap-2"
                    disabled={loading || !hasContext}
                >
                    <RefreshCw className="h-4 w-4" />
                    Refresh
                </button>
            </div>

            {!hasContext && !onboardingLoading ? (
                <div className="mo-card rounded-2xl border border-dashed border-[#2A2A2A] bg-[#111111] px-6 py-10 text-center">
                    <FileText className="mx-auto mb-4 h-12 w-12 text-[#2F2F2F]" />
                    <div className="text-lg font-semibold text-white">Organization setup is incomplete</div>
                    <div className="mt-2 text-sm text-[#A0A0A0]">
                        Finish onboarding so the documents library can load the correct organization data.
                    </div>
                </div>
            ) : (
                <div className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
                    <div className="mo-card">
                        <div className="mb-4">
                            <h2 className="mo-h2">Upload Document</h2>
                            <p className="mo-text-secondary mt-1">
                                Attach metadata so the document can be linked and found later.
                            </p>
                        </div>

                        <div className="space-y-4">
                            <div className="rounded-2xl border border-dashed border-[#2A2A2A] bg-[#111111] p-4">
                                <input
                                    key={fileInputKey}
                                    type="file"
                                    onChange={handleFileSelection}
                                    className="block w-full text-sm text-white"
                                />

                                {selectedFile ? (
                                    <div className="mt-3 rounded-xl border border-[#2A2A2A] bg-[#0E0E0E] p-3 text-sm text-[#A0A0A0]">
                                        <div className="font-medium text-white">{selectedFile.name}</div>
                                        <div className="mt-1">{formatFileSize(selectedFile.size)}</div>
                                    </div>
                                ) : null}
                            </div>

                            <div className="grid gap-4">
                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Display name</label>
                                    <input
                                        value={uploadForm.name}
                                        onChange={(event) => updateUploadField("name", event.target.value)}
                                        className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none"
                                        placeholder="Agreement - April 2026"
                                    />
                                </div>

                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Type</label>
                                    <select
                                        value={uploadForm.type}
                                        onChange={(event) => updateUploadField("type", event.target.value)}
                                        className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none"
                                    >
                                        {TYPE_OPTIONS.filter((option) => option.value !== "ALL").map((option) => (
                                            <option key={option.value} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Category</label>
                                    <input
                                        value={uploadForm.category}
                                        onChange={(event) => updateUploadField("category", event.target.value)}
                                        className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none"
                                        placeholder="Operations"
                                    />
                                </div>

                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Linked entity type</label>
                                    <select
                                        value={uploadForm.linkedEntityType}
                                        onChange={(event) => updateUploadField("linkedEntityType", event.target.value)}
                                        className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none"
                                    >
                                        {ENTITY_OPTIONS.map((option) => (
                                            <option key={option.value || "none"} value={option.value}>
                                                {option.label}
                                            </option>
                                        ))}
                                    </select>
                                </div>

                                {uploadForm.linkedEntityType ? (
                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium text-[#A0A0A0]">Linked entity ID</label>
                                        <input
                                            value={uploadForm.linkedEntityId}
                                            onChange={(event) => updateUploadField("linkedEntityId", event.target.value)}
                                            className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none"
                                            placeholder="Paste invoice or client ID"
                                        />
                                    </div>
                                ) : null}

                                <div className="grid gap-2">
                                    <label className="text-sm font-medium text-[#A0A0A0]">Summary</label>
                                    <textarea
                                        value={uploadForm.contentSummary}
                                        onChange={(event) => updateUploadField("contentSummary", event.target.value)}
                                        className="min-h-24 rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none"
                                        placeholder="Optional notes about the file"
                                    />
                                </div>

                                <label className="flex items-center gap-3 rounded-xl border border-[#2A2A2A] bg-[#111111] px-3 py-3 text-sm text-white">
                                    <input
                                        type="checkbox"
                                        checked={uploadForm.isConfidential}
                                        onChange={(event) => updateUploadField("isConfidential", event.target.checked)}
                                    />
                                    Mark as confidential
                                </label>
                            </div>

                            {uploading ? (
                                <div className="space-y-2">
                                    <Progress value={uploadProgress} />
                                    <div className="text-xs text-[#A0A0A0]">Uploading... {uploadProgress}%</div>
                                </div>
                            ) : null}

                            <button
                                onClick={handleUpload}
                                disabled={!selectedFile || uploading || !hasContext}
                                className="mo-btn-primary flex w-full items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-70"
                            >
                                {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                                {uploading ? "Uploading..." : "Upload Document"}
                            </button>
                        </div>
                    </div>

                    <div className="mo-card">
                        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <h2 className="mo-h2">Document Library</h2>
                                <p className="mo-text-secondary mt-1">
                                    Showing {showingFrom}-{showingTo} of {totalElements} documents
                                </p>
                            </div>

                            <div className="flex items-center gap-2">
                                <Filter className="h-4 w-4 text-[#A0A0A0]" />
                                <select
                                    value={filterType}
                                    onChange={(event) => setFilterType(event.target.value)}
                                    className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white outline-none"
                                >
                                    {TYPE_OPTIONS.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        {loading || onboardingLoading ? (
                            <div className="flex items-center justify-center py-20">
                                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
                            </div>
                        ) : documents.length === 0 ? (
                            <div className="rounded-2xl border border-dashed border-[#2A2A2A] bg-[#111111] px-4 py-16 text-center">
                                <FileText className="mx-auto mb-4 h-12 w-12 text-[#2F2F2F]" />
                                <div className="text-lg font-semibold text-white">No documents found</div>
                                <div className="mt-2 text-sm text-[#A0A0A0]">
                                    Upload a file or change the type filter to see more results.
                                </div>
                            </div>
                        ) : (
                            <>
                                <div className="overflow-x-auto rounded-xl border border-[#202020]">
                                    <table className="w-full min-w-[860px] text-sm">
                                        <thead className="bg-[#161616]">
                                            <tr>
                                                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">
                                                    Name
                                                </th>
                                                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">
                                                    Type
                                                </th>
                                                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">
                                                    Size
                                                </th>
                                                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">
                                                    Uploaded By
                                                </th>
                                                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">
                                                    Created
                                                </th>
                                                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">
                                                    Linked Entity
                                                </th>
                                                <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">
                                                    Actions
                                                </th>
                                            </tr>
                                        </thead>

                                        <tbody className="divide-y divide-[#1F1F1F]">
                                            {documents.map((doc) => (
                                                <tr key={doc.id} className="bg-[#101010]">
                                                    <td className="px-4 py-3">
                                                        <div className="font-medium text-white">{doc.name}</div>
                                                        <div className="mt-1 text-xs text-[#A0A0A0]">
                                                            {doc.mimeType || "Unknown type"}
                                                        </div>
                                                    </td>
                                                    <td className="px-4 py-3 text-[#A0A0A0]">{doc.type || "OTHER"}</td>
                                                    <td className="px-4 py-3 text-right text-[#A0A0A0]">
                                                        {formatFileSize(doc.size)}
                                                    </td>
                                                    <td className="px-4 py-3 text-[#A0A0A0]">{doc.uploadedBy || "--"}</td>
                                                    <td className="px-4 py-3 text-[#A0A0A0]">{formatDate(doc.createdAt)}</td>
                                                    <td className="px-4 py-3">
                                                        {doc.linkedEntityType && doc.linkedEntityId ? (
                                                            <button
                                                                onClick={() => handleLinkedEntityNavigation(doc)}
                                                                className="inline-flex items-center gap-1 rounded-lg border border-[#2A2A2A] px-2 py-1 text-xs text-[#60A5FA] transition hover:border-[#60A5FA50]"
                                                            >
                                                                <Link2 className="h-3 w-3" />
                                                                {doc.linkedEntityType} {doc.linkedEntityId.slice(0, 8)}
                                                            </button>
                                                        ) : (
                                                            <span className="text-[#666666]">Not linked</span>
                                                        )}
                                                    </td>
                                                    <td className="px-4 py-3">
                                                        <div className="flex justify-end gap-2">
                                                            <button
                                                                onClick={() => handleDownload(doc)}
                                                                className="rounded-lg border border-[#2A2A2A] p-2 text-[#A0A0A0] transition hover:text-white"
                                                                disabled={downloadingDocumentId === doc.id}
                                                                title="Download"
                                                            >
                                                                {downloadingDocumentId === doc.id ? (
                                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                                ) : (
                                                                    <Download className="h-4 w-4" />
                                                                )}
                                                            </button>

                                                            <button
                                                                onClick={() => handleDelete(doc.id)}
                                                                className="rounded-lg border border-[#CD1C1840] p-2 text-[#CD1C18] transition hover:bg-[#CD1C1812]"
                                                                disabled={deletingDocumentId === doc.id}
                                                                title="Delete"
                                                            >
                                                                {deletingDocumentId === doc.id ? (
                                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                                ) : (
                                                                    <Trash2 className="h-4 w-4" />
                                                                )}
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>

                                <div className="mt-4 flex items-center justify-between gap-3">
                                    <div className="text-sm text-[#A0A0A0]">
                                        Page {pageNumber + 1} of {Math.max(totalPages, 1)}
                                    </div>

                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => fetchDocuments(Math.max(pageNumber - 1, 0), filterType)}
                                            disabled={pageNumber === 0}
                                            className="mo-btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                            Previous
                                        </button>

                                        <button
                                            onClick={() => fetchDocuments(pageNumber + 1, filterType)}
                                            disabled={pageNumber + 1 >= totalPages}
                                            className="mo-btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                            Next
                                        </button>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
