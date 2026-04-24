import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";

/**
 * Protects dashboard routes:
 *   1. If not signed in  → /sign-in
 *   2. If signed in but onboarding not done → /onboarding
 *   3. If onboarding done → render children (dashboard)
 *
 * The /onboarding route itself is excluded from the onboarding check
 * so users don't end up in a redirect loop.
 */
export function ProtectedRoute({ children }) {
    const { isLoaded, isSignedIn } = useAuth();
    const { loading, complete, error, statusMessage, refetch } = useOnboardingStatus();
    const location = useLocation();

    const isOnboardingRoute = location.pathname === "/onboarding";

    // ── 1. Clerk not yet loaded ────────────────────────────────────────────────
    if (!isLoaded) {
        return <Spinner />;
    }

    // ── 2. Not signed in → login page ─────────────────────────────────────────
    if (!isSignedIn) {
        return <Navigate to="/sign-in" state={{ from: location }} replace />;
    }

    // ── 3. Waiting for onboarding status from backend ──────────────────────────
    if (loading) {
        return <Spinner />;
    }

    if (error && !isOnboardingRoute) {
        return <StatusError message={statusMessage} onRetry={refetch} />;
    }

    // ── 4. Onboarding not complete → send to /onboarding ──────────────────────
    if (!complete && !isOnboardingRoute) {
        return <Navigate to="/onboarding" replace />;
    }

    // ── 5. Already complete but on /onboarding → send to dashboard ────────────
    if (complete && isOnboardingRoute) {
        return <Navigate to="/finances" replace />;
    }

    return children;
}

function Spinner() {
    return (
        <div className="flex min-h-screen items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
    );
}

function StatusError({ message, onRetry }) {
    return (
        <div className="flex min-h-screen items-center justify-center bg-black p-4">
            <div className="max-w-md rounded-2xl border border-[#2A2A2A] bg-[#111111] p-6 text-center">
                <h1 className="mb-2 text-xl font-bold text-white">Workspace check failed</h1>
                <p className="mb-5 text-sm leading-6 text-[#A0A0A0]">
                    {message || "MoneyOps could not verify your workspace yet."}
                </p>
                <button type="button" className="mo-btn-primary" onClick={onRetry}>
                    Retry
                </button>
            </div>
        </div>
    );
}
