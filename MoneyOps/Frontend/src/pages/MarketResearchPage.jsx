import { useEffect, useState } from "react";
import { useAuth } from "@clerk/clerk-react";
import { MarketResearchDashboard } from "@/components/MarketResearchDashboard";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export default function MarketResearchPage() {
    const [isHydrated, setIsHydrated] = useState(false);
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState(null);
    const { orgId, userId } = useAuth();

    useEffect(() => {
        setIsHydrated(true);
        if (orgId) fetchMarketData();
    }, [orgId]);

    async function fetchMarketData() {
        setLoading(true);
        try {
            // Directly fetch market intelligence from AI Gateway using the Clerk orgId.
            // Our backend adapter resolves the orgId to an internal UUID automatically.
            const res = await fetch(
                `http://localhost:8001/api/v1/market/intelligence?org_uuid=${orgId}&business_id=1&user_id=${userId || ""}`,
                { headers: { "Content-Type": "application/json" } }
            );
            const json = await res.json();
            if (json.success) {
                setData(json);
                if (json.cached) {
                    toast.info("Showing cached market data", { duration: 2000 });
                }
            }
        } catch (error) {
            console.error(error);
            toast.error("Failed to load market data");
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
            <MarketResearchDashboard
                businessId={1}
                data={data}
                onRefresh={fetchMarketData}
            />
        </div>
    );
}
