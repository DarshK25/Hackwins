import { SignIn } from "@clerk/clerk-react";
import { useLocation } from "react-router-dom";

export default function SignInPage() {
    const location = useLocation();
    const from = (location.state?.from?.pathname) || "/analytics";

    return (
        <div className="flex min-h-screen items-center justify-center bg-muted/30">
            <SignIn
                routing="path"
                path="/sign-in"
                signUpUrl="/sign-up"
                afterSignInUrl={from}
                redirectUrl={from}
            />
        </div>
    );
}
