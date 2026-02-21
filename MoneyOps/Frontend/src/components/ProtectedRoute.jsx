import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@clerk/clerk-react";

/**
 * Protects routes - redirects to /sign-in if not authenticated.
 * Does not modify backend/API Gateway auth.
 */
export function ProtectedRoute({ children }) {
    const { isLoaded, isSignedIn } = useAuth();
    const location = useLocation();

    if (!isLoaded) {
        return (
            <div className="flex min-h-screen items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
        );
    }

    if (!isSignedIn) {
        return <Navigate to="/sign-in" state={{ from: location }} replace />;
    }

    return children;
}
