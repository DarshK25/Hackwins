import { useEffect, useState } from "react";
import { ComplianceDashboard } from "@/components/ComplianceDashboard";
import { Loader2 } from "lucide-react";

export default function CompliancePage() {
    const [isHydrated, setIsHydrated] = useState(false);
    const [businessId, setBusinessId] = useState(1);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setIsHydrated(true);
        setBusinessId(1);
        setLoading(false);
    }, []);

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
                onRefresh={() => {}}
            />
        </div>
    );
}
