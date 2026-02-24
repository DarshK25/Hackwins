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
    const { loading, complete } = useOnboardingStatus();
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
