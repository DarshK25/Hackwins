import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useUser } from "@clerk/clerk-react";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Building2, Users } from "lucide-react";
import { toast } from "sonner";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";

import { BusinessInfoStep } from "@/components/onboarding/BusinessInfoStep";
import { RegulatoryInfoStep } from "@/components/onboarding/RegulatoryInfoStep";
import { BusinessContextStep } from "@/components/onboarding/BusinessContextStep";
import { InviteCodeStep } from "@/components/onboarding/InviteCodeStep";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

// Step sequences per mode
const STEP_SEQUENCES = {
    "new-business": ["business-info", "regulatory", "context"],
    "join-business": ["invite"],
};

export default function OnboardingPage() {
    const { user } = useUser();
    const navigate = useNavigate();
    const { refetch } = useOnboardingStatus();
    const [mode, setMode] = useState("choose"); // 'choose' | 'new-business' | 'join-business'
    const [currentStep, setCurrentStep] = useState("welcome");
    const [formData, setFormData] = useState({});
    const [loading, setLoading] = useState(false);

    const steps = STEP_SEQUENCES[mode] ?? [];
    const currentStepIndex = steps.indexOf(currentStep);
    const progress = steps.length ? ((currentStepIndex + 1) / steps.length) * 100 : 0;

    // ─── Handlers ─────────────────────────────────────────────────────────────

    const handleModeSelect = (selectedMode) => {
        setMode(selectedMode);
        setCurrentStep(STEP_SEQUENCES[selectedMode][0]);
    };

    const handleNext = (stepData) => {
        const updatedData = { ...formData, ...stepData };
        setFormData(updatedData);

        const nextIndex = currentStepIndex + 1;
        if (nextIndex < steps.length) {
            setCurrentStep(steps[nextIndex]);
        } else {
            handleSubmit(updatedData);
        }
    };

    const handleBack = () => {
        if (currentStepIndex > 0) {
            setCurrentStep(steps[currentStepIndex - 1]);
        } else {
            // Go back to welcome screen
            setMode("choose");
            setCurrentStep("welcome");
        }
    };

    const handleSubmit = async (finalData) => {
        setLoading(true);
        try {
            const endpoint =
                mode === "new-business"
                    ? `${BACKEND_URL}/api/onboarding/create-business`
                    : `${BACKEND_URL}/api/onboarding/join-business`;

            // Build payload:
            // - legalName  = company name from Step 1 (sent as "name" by BusinessInfoStep)
            // - name       = Clerk user's personal name (stored on the User document)
            const payload = {
                ...finalData,
                legalName: finalData.name,          // company name from Step 1
                clerkId: user?.id,
                email: user?.primaryEmailAddress?.emailAddress,
                name: user?.fullName || user?.firstName || "User", // person's name
            };

            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || error.message || "Failed to complete onboarding");
            }

            toast.success("Welcome to MoneyOps! Taking you to your dashboard…");
            await refetch();
            setTimeout(() => navigate("/finances", { replace: true }), 1200);
        } catch (error) {
            console.error("Onboarding error:", error);
            toast.error(error.message || "Failed to complete onboarding. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    // ─── Welcome / Mode-select screen ─────────────────────────────────────────

    if (currentStep === "welcome") {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-slate-50 p-4">
                <Card className="w-full max-w-4xl">
                    <CardHeader className="text-center pb-2">
                        <CardTitle className="text-3xl font-bold">Welcome to LedgerTalk!</CardTitle>
                        <CardDescription className="text-lg mt-2">
                            Let's get you set up. Choose an option to continue.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="grid gap-6 md:grid-cols-2 mt-6">
                            {/* New Business */}
                            <button
                                type="button"
                                onClick={() => handleModeSelect("new-business")}
                                className="group h-auto flex flex-col items-center gap-4 p-8 rounded-xl border-2 border-slate-200 bg-white hover:border-blue-500 hover:bg-blue-50/40 transition-all duration-200 text-left"
                            >
                                <Building2 className="h-16 w-16 text-blue-600 group-hover:scale-110 transition-transform" />
                                <div className="text-center">
                                    <div className="font-semibold text-lg">Create New Business</div>
                                    <div className="text-sm text-slate-500 mt-1">
                                        Set up a new business account with your details
                                    </div>
                                </div>
                            </button>

                            {/* Join Existing */}
                            <button
                                type="button"
                                onClick={() => handleModeSelect("join-business")}
                                className="group h-auto flex flex-col items-center gap-4 p-8 rounded-xl border-2 border-slate-200 bg-white hover:border-blue-500 hover:bg-blue-50/40 transition-all duration-200 text-left"
                            >
                                <Users className="h-16 w-16 text-blue-600 group-hover:scale-110 transition-transform" />
                                <div className="text-center">
                                    <div className="font-semibold text-lg">Join Existing Business</div>
                                    <div className="text-sm text-slate-500 mt-1">
                                        Enter an invite code to join your team
                                    </div>
                                </div>
                            </button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // ─── Multi-step form ───────────────────────────────────────────────────────

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-slate-50 p-4">
            <Card className="w-full max-w-3xl">
                <CardHeader>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <CardTitle>
                                {mode === "new-business" ? "Business Onboarding" : "Join Business"}
                            </CardTitle>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={handleBack}
                                disabled={loading}
                            >
                                ← Back
                            </Button>
                        </div>

                        {/* Progress bar */}
                        <Progress value={progress} className="h-2" />

                        <CardDescription>
                            Step {currentStepIndex + 1} of {steps.length}
                        </CardDescription>
                    </div>
                </CardHeader>

                <CardContent>
                    {currentStep === "business-info" && (
                        <BusinessInfoStep
                            initialData={formData}
                            onNext={handleNext}
                            loading={loading}
                        />
                    )}
                    {currentStep === "regulatory" && (
                        <RegulatoryInfoStep
                            initialData={formData}
                            onNext={handleNext}
                            onBack={handleBack}
                            loading={loading}
                        />
                    )}
                    {currentStep === "context" && (
                        <BusinessContextStep
                            initialData={formData}
                            onNext={handleNext}
                            onBack={handleBack}
                            loading={loading}
                        />
                    )}
                    {currentStep === "invite" && (
                        <InviteCodeStep onNext={handleNext} loading={loading} />
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
