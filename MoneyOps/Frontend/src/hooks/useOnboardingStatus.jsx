import { createContext, useContext, useEffect, useState } from "react";
import { useUser } from "@clerk/clerk-react";

const OnboardingContext = createContext(null);

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export function OnboardingProvider({ children }) {
    const { user, isLoaded } = useUser();

    const [loading, setLoading] = useState(true);
    const [complete, setComplete] = useState(false);
    const [userId, setUserId] = useState(null);
    const [orgId, setOrgId] = useState(null);

    const check = async () => {
        if (!isLoaded || !user) {
            setLoading(false);
            return;
        }
        setLoading(true);
        try {
            const res = await fetch(
                `${BACKEND_URL}/api/onboarding/status?clerkId=${user.id}`
            );
            if (!res.ok) throw new Error("Status check failed");
            const json = await res.json();
            const data = json.data ?? json;
            setComplete(data.onboardingComplete ?? false);
            setUserId(data.userId ?? null);
            setOrgId(data.orgId ?? null);
        } catch (err) {
            console.error("Onboarding status check failed:", err);
            setComplete(false);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isLoaded) {
            check();
        }
    }, [isLoaded, user?.id]);

    return (
        <OnboardingContext.Provider value={{ loading, complete, userId, orgId, refetch: check }}>
            {children}
        </OnboardingContext.Provider>
    );
}

export function useOnboardingStatus() {
    const context = useContext(OnboardingContext);
    if (!context) {
        throw new Error("useOnboardingStatus must be used within an OnboardingProvider");
    }
    return context;
}
