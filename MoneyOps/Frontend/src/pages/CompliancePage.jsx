import { useEffect, useState } from "react";
import { ComplianceDashboard } from "@/components/ComplianceDashboard";
import { Loader2 } from "lucide-react";
import { useAuth } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";

export default function CompliancePage() {
    const { getToken } = useAuth();
    const { userId: internalUserId, orgId: internalOrgId, loading: onboardingLoading } = useOnboardingStatus();
    const [isHydrated, setIsHydrated] = useState(false);
    const [businessId] = useState(1);
    const [loading, setLoading] = useState(true);
    const [complianceData, setComplianceData] = useState(null);
    const [summaryData, setSummaryData] = useState(null);

    async function fetchComplianceStatus() {
        if (!internalUserId || !internalOrgId) {
            setLoading(false);
            return;
        }

        setLoading(true);
        try {
            const token = await getToken();
            const headers = {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`,
                "X-User-Id": internalUserId,
                "X-Org-Id": internalOrgId,
            };

            const [statusRes, summaryRes] = await Promise.all([
                fetch(`/api/compliance/status?businessId=${businessId}&userId=${internalUserId}`, { headers }),
                fetch(`/api/compliance/summary?orgId=${internalOrgId}`, { headers })
            ]);

            if (!statusRes.ok) throw new Error("Failed to fetch compliance status");
            if (!summaryRes.ok) throw new Error("Failed to fetch compliance summary");

            const [statusData, summaryJson] = await Promise.all([
                statusRes.json(),
                summaryRes.json()
            ]);

            setComplianceData(statusData);
            setSummaryData(summaryJson);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        setIsHydrated(true);
    }, []);

    useEffect(() => {
        if (!onboardingLoading) {
            fetchComplianceStatus();
        }
    }, [onboardingLoading, internalUserId, internalOrgId]);

    if (!isHydrated || loading || onboardingLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            <ComplianceDashboard
                businessId={businessId}
                data={complianceData}
                summaryData={summaryData}
                onRefresh={fetchComplianceStatus}
            />
        </div>
    );
}
