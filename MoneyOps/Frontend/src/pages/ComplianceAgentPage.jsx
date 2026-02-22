import { useEffect, useState } from "react";
import { ComplianceDashboard } from "@/components/ComplianceDashboard";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export default function ComplianceAgentPage() {
    const [isHydrated, setIsHydrated] = useState(false);
    const [businessId, setBusinessId] = useState(1);
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState(null);

    useEffect(() => {
        setIsHydrated(true);
        initBusiness();
    }, []);

    async function initBusiness() {
        try {
            // Simulate fetch
            // const initRes = await fetch("/api/init");
            // const initData = await initRes.json();
            // const bId = initData.business?.id || 1;
            setBusinessId(1);
        } catch (error) {
            console.error(error);
            toast.error("Failed to load compliance data");
        } finally {
            setLoading(false);
        }
    }

    if (!isHydrated || loading) {
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
                data={data}
                onRefresh={() => initBusiness()}
            />
        </div>
    );
}
