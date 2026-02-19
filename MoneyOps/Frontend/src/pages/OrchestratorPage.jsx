import { useEffect, useState } from "react";
import { OrchestratorDashboard } from "@/components/OrchestratorDashboard";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export default function OrchestratorPage() {
    const [isHydrated, setIsHydrated] = useState(false);
    const [businessId, setBusinessId] = useState(1);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        setIsHydrated(true);
        initBusiness();
    }, []);

    async function initBusiness() {
        try {
            setBusinessId(1);
        } catch (error) {
            console.error(error);
            toast.error("Failed to initialize");
        } finally {
            setLoading(false);
        }
    }

    if (!isHydrated || loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-slate-50">
                <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
        );
    }

    return (
        <div className="space-y-4 p-4 md:p-6">
            <OrchestratorDashboard businessId={businessId} />
        </div>
    );
}
