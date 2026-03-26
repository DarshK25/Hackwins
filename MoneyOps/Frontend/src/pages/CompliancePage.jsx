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

            const backendRes = await fetch(`/api/compliance/status?businessId=${businessId}&userId=${internalUserId}`, { headers });
            if (!backendRes.ok) {
                throw new Error("Failed to fetch compliance status");
            }
            const backendData = await backendRes.json();
            setComplianceData(backendData);
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
                onRefresh={fetchComplianceStatus}
            />
        </div>
    );
}
