import { SignUp } from "@clerk/clerk-react";

export default function SignUpPage() {
    return (
        <div className="flex min-h-screen items-center justify-center bg-muted/30">
            <SignUp
                routing="path"
                path="/sign-up"
                signInUrl="/sign-in"
                afterSignUpUrl="/analytics"
                redirectUrl="/analytics"
            />
        </div>
    );
}
