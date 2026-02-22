import { useEffect, useState } from "react";
import { SalesCRMDashboard } from "@/components/SalesCRMDashboard";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export default function SalesCRMPage() {
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
            setBusinessId(1);
        } catch (error) {
            console.error(error);
            toast.error("Failed to load sales data");
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
            <SalesCRMDashboard
                businessId={businessId}
                data={data}
                onRefresh={() => initBusiness()}
            />
        </div>
    );
}
