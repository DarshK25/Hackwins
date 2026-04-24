import { useState, useEffect } from "react";
import { useAuth } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { Loader2, ChevronLeft, ChevronRight, FileText } from "lucide-react";
import { toast } from "sonner";
import { formatAppDateTime } from "@/lib/dateTime";

export default function AuditLogPage() {
    const { getToken } = useAuth();
    const { userId: internalUserId, orgId: internalOrgId } = useOnboardingStatus();
    
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(0);
    const [totalPages, setTotalPages] = useState(1);
    const [totalElements, setTotalElements] = useState(0);
    const size = 15;

    useEffect(() => {
        if (internalUserId && internalOrgId) {
            fetchLogs(page);
        }
    }, [internalUserId, internalOrgId, page]);

    const fetchLogs = async (pageNumber) => {
        setLoading(true);
        try {
            const token = await getToken();
            const res = await fetch(`/api/audit?page=${pageNumber}&size=${size}`, {
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "X-User-Id": internalUserId,
                    "X-Org-Id": internalOrgId
                }
            });
            if (!res.ok) throw new Error("Failed to fetch audit logs");
            
            const result = await res.json();
            if (result.success && result.data) {
                setLogs(result.data.content || []);
                setTotalPages(result.data.totalPages || 1);
                setTotalElements(result.data.totalElements || 0);
            }
        } catch (error) {
            console.error(error);
            toast.error("Could not load audit logs");
        } finally {
            setLoading(false);
        }
    };

    const handlePrev = () => {
        if (page > 0) setPage(page - 1);
    };

    const handleNext = () => {
        if (page < totalPages - 1) setPage(page + 1);
    };

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="mo-h1 flex items-center gap-2">
                        <FileText className="h-6 w-6 text-[#4CBB17]" />
                        Audit Logs
                    </h1>
                    <p className="mo-text-secondary mt-1">Track system activity and data changes</p>
                </div>
                <div className="text-sm text-[#A0A0A0]">
                    Total Records: <span className="text-white font-medium">{totalElements}</span>
                </div>
            </div>

            <div className="mo-card p-0 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-[#1A1A1A] text-[#A0A0A0] text-xs uppercase border-b border-[#2A2A2A]">
                            <tr>
                                <th className="px-6 py-4 font-medium">Timestamp</th>
                                <th className="px-6 py-4 font-medium">Entity</th>
                                <th className="px-6 py-4 font-medium">Operation</th>
                                <th className="px-6 py-4 font-medium">User ID</th>
                                <th className="px-6 py-4 font-medium">IP Address</th>
                                <th className="px-6 py-4 font-medium">User Agent</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#2A2A2A]">
                            {loading && logs.length === 0 ? (
                                <tr>
                                    <td colSpan="6" className="px-6 py-12 text-center">
                                        <Loader2 className="h-6 w-6 animate-spin text-[#4CBB17] mx-auto mb-2" />
                                        <p className="text-[#A0A0A0]">Loading logs...</p>
                                    </td>
                                </tr>
                            ) : logs.length === 0 ? (
                                <tr>
                                    <td colSpan="6" className="px-6 py-12 text-center text-[#A0A0A0]">
                                        No audit logs found.
                                    </td>
                                </tr>
                            ) : (
                                logs.map((log, index) => (
                                    <tr key={log.id || `${log.entityId || "audit-log"}-${index}`} className="hover:bg-[#1A1A1A]/50 transition-colors">
                                        <td className="px-6 py-4 text-white whitespace-nowrap">
                                            {formatAppDateTime(log.timestamp)}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-white font-medium">{log.entityType}</span>
                                            <div className="text-xs text-[#A0A0A0] mt-0.5 truncate max-w-[120px]" title={log.entityId}>
                                                {log.entityId}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                                                log.operation === 'CREATE' ? 'bg-[#4CBB1720] text-[#4CBB17] border border-[#4CBB1740]' :
                                                log.operation === 'UPDATE' ? 'bg-[#60A5FA20] text-[#60A5FA] border border-[#60A5FA40]' :
                                                log.operation === 'DELETE' ? 'bg-[#CD1C1820] text-[#CD1C18] border border-[#CD1C1840]' :
                                                'bg-[#2A2A2A] text-white border border-[#444]'
                                            }`}>
                                                {log.operation}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-white text-xs truncate max-w-[120px]" title={log.userId}>
                                                {log.userId || "—"}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-[#A0A0A0]">
                                            {log.ipAddress || "—"}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-[#A0A0A0] text-xs truncate max-w-[200px]" title={log.userAgent}>
                                                {log.userAgent || "—"}
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination Controls */}
                <div className="flex items-center justify-between px-6 py-4 border-t border-[#2A2A2A] bg-[#111111]">
                    <div className="text-sm text-[#A0A0A0]">
                        Showing page <span className="text-white font-medium">{page + 1}</span> of <span className="text-white font-medium">{totalPages || 1}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handlePrev}
                            disabled={page === 0 || loading}
                            className="p-2 rounded-lg bg-[#1A1A1A] border border-[#2A2A2A] text-white hover:bg-[#2A2A2A] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronLeft className="h-4 w-4" />
                        </button>
                        <button
                            onClick={handleNext}
                            disabled={page >= totalPages - 1 || loading}
                            className="p-2 rounded-lg bg-[#1A1A1A] border border-[#2A2A2A] text-white hover:bg-[#2A2A2A] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <ChevronRight className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
