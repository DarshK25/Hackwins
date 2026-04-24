import { createContext, useContext, useEffect, useState } from "react";
import { useUser } from "@clerk/clerk-react";

const OnboardingContext = createContext(null);

const BACKEND_URL = ""; // Use Vite proxy via relative paths

export function OnboardingProvider({ children }) {
    const { user, isLoaded } = useUser();

    const [loading, setLoading] = useState(true);
    const [complete, setComplete] = useState(false);
    const [userId, setUserId] = useState(null);
    const [orgId, setOrgId] = useState(null);
    const [statusMessage, setStatusMessage] = useState("");
    const [error, setError] = useState(null);

    const reset = () => {
        setComplete(false);
        setUserId(null);
        setOrgId(null);
        setStatusMessage("");
        setError(null);
    };

    const check = async () => {
        if (!isLoaded || !user) {
            reset();
            setLoading(false);
            return;
        }
        setLoading(true);
        setError(null);
        try {
            const email = user.primaryEmailAddress?.emailAddress ?? "";
            const params = new URLSearchParams({ clerkId: user.id });
            if (email) {
                params.set("email", email);
            }

            const res = await fetch(
                `${BACKEND_URL}/api/onboarding/status?${params.toString()}`,
                {
                    headers: {
                        "X-User-Id": user.id,
                        ...(email ? { "X-User-Email": email } : {})
                    }
                }
            );
            if (!res.ok) throw new Error(`Status check failed (${res.status})`);
            const json = await res.json();
            const data = json.data ?? json;
            setComplete(data.onboardingComplete ?? false);
            setUserId(data.userId ?? null);
            setOrgId(data.orgId ?? null);
            setStatusMessage(data.message ?? "");
        } catch (err) {
            console.error("Onboarding status check failed:", err);
            setComplete(false);
            setUserId(null);
            setOrgId(null);
            setStatusMessage("Unable to verify your workspace. Please make sure the backend is running and try again.");
            setError(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isLoaded) {
            check();
        }
    }, [isLoaded, user?.id, user?.primaryEmailAddress?.emailAddress]);

    return (
        <OnboardingContext.Provider value={{ loading, complete, userId, orgId, statusMessage, error, refetch: check, reset }}>
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
