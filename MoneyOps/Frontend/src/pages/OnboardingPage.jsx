import { useState } from "react";
import { Building2, Users, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Progress } from "@/components/ui/progress";
import { useUser } from "@clerk/clerk-react";

import { BusinessInfoStep } from "@/components/onboarding/BusinessInfoStep";
import { RegulatoryInfoStep } from "@/components/onboarding/RegulatoryInfoStep";
import { BusinessContextStep } from "@/components/onboarding/BusinessContextStep";
import { InviteCodeStep } from "@/components/onboarding/InviteCodeStep";

const STEP_SEQUENCES = {
    "new-business": ["business-info", "regulatory", "context"],
    "join-business": ["invite"],
};

export default function OnboardingPage() {
    const { user } = useUser();
    const [mode, setMode] = useState("choose");
    const [currentStep, setCurrentStep] = useState("welcome");
    const [formData, setFormData] = useState({});
    const [loading, setLoading] = useState(false);

    const steps = STEP_SEQUENCES[mode] ?? [];
    const currentStepIndex = steps.indexOf(currentStep);
    const progress = steps.length ? ((currentStepIndex + 1) / steps.length) * 100 : 0;

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
            setMode("choose");
            setCurrentStep("welcome");
        }
    };

    const handleSubmit = async (finalData) => {
        setLoading(true);
        try {
            const payload = {
                ...finalData,
                clerkId: user?.id,
                email: user?.primaryEmailAddress?.emailAddress,
                name: user?.fullName || user?.firstName,
            };

            const endpoint = mode === "new-business"
                ? "/api/onboarding/create-business"
                : "/api/onboarding/join-business";
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-User-Id": user?.id
                },
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || "Failed to complete onboarding");
            }
            toast.success("Onboarding completed! Redirecting to dashboard…");
            setTimeout(() => { window.location.href = "/analytics"; }, 1500);
        } catch (error) {
            console.error("Onboarding error:", error);
            toast.error(error.message || "Failed to complete onboarding");
        } finally {
            setLoading(false);
        }
    };

    // ── Welcome screen ────────────────────────────────────────────────────────

    if (currentStep === "welcome") {
        return (
            <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: "#000000" }}>
                <div className="w-full max-w-4xl">
                    {/* Logo / Brand */}
                    <div className="text-center mb-10">
                        <div className="inline-flex items-center gap-2 mb-3">
                            <div className="h-8 w-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#4CBB17" }}>
                                <span className="text-black font-bold text-sm">M</span>
                            </div>
                            <span className="text-2xl font-bold text-white">MoneyOps</span>
                        </div>
                        <h1 className="text-4xl font-bold text-white mb-3">Welcome to MoneyOps!</h1>
                        <p className="text-[#A0A0A0] text-lg">Let's get you set up. Choose an option to continue.</p>
                    </div>

                    {/* Mode cards */}
                    <div className="grid gap-6 md:grid-cols-2">
                        {[
                            {
                                mode: "new-business",
                                icon: Building2,
                                title: "Create New Business",
                                desc: "Set up a new business account with your details",
                            },
                            {
                                mode: "join-business",
                                icon: Users,
                                title: "Join Existing Business",
                                desc: "Enter an invite code to join your team",
                            },
                        ].map(({ mode: m, icon: Icon, title, desc }) => (
                            <button
                                key={m}
                                type="button"
                                onClick={() => handleModeSelect(m)}
                                className="group flex flex-col items-center gap-4 p-8 rounded-2xl text-center transition-all duration-200 hover:scale-105"
                                style={{ backgroundColor: "#111111", border: "1px solid #2A2A2A" }}
                                onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#4CBB17"; e.currentTarget.style.boxShadow = "0 0 20px #4CBB1715"; }}
                                onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#2A2A2A"; e.currentTarget.style.boxShadow = "none"; }}
                            >
                                <div className="h-20 w-20 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform" style={{ backgroundColor: "#4CBB1715" }}>
                                    <Icon className="h-10 w-10 text-[#4CBB17]" />
                                </div>
                                <div>
                                    <div className="font-bold text-xl text-white mb-1">{title}</div>
                                    <div className="text-sm text-[#A0A0A0]">{desc}</div>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // ── Multi-step form ───────────────────────────────────────────────────────

    return (
        <div className="min-h-screen dark flex items-center justify-center p-4" style={{ backgroundColor: "#000000" }}>
            <div className="w-full max-w-3xl rounded-2xl p-8" style={{ backgroundColor: "#111111", border: "1px solid #2A2A2A" }}>
                <div className="flex items-center justify-between mb-2">
                    <h2 className="text-xl font-bold text-white">
                        {mode === "new-business" ? "Business Onboarding" : "Join Business"}
                    </h2>
                    <button
                        className="text-sm text-[#A0A0A0] hover:text-[#4CBB17] transition-colors disabled:opacity-40"
                        onClick={handleBack}
                        disabled={loading}
                    >
                        ← Back
                    </button>
                </div>

                {/* Progress bar */}
                <div className="mb-2">
                    <div className="h-1.5 w-full rounded-full bg-[#2A2A2A]">
                        <div
                            className="h-full rounded-full transition-all duration-300"
                            style={{ width: `${progress}%`, backgroundColor: "#4CBB17" }}
                        />
                    </div>
                </div>
                <p className="text-xs text-[#A0A0A0] mb-8">Step {currentStepIndex + 1} of {steps.length}</p>

                {currentStep === "business-info" && (
                    <BusinessInfoStep initialData={formData} onNext={handleNext} loading={loading} />
                )}
                {currentStep === "regulatory" && (
                    <RegulatoryInfoStep initialData={formData} onNext={handleNext} onBack={handleBack} loading={loading} />
                )}
                {currentStep === "context" && (
                    <BusinessContextStep initialData={formData} onNext={handleNext} onBack={handleBack} loading={loading} />
                )}
                {currentStep === "invite" && (
                    <InviteCodeStep onNext={handleNext} loading={loading} />
                )}
            </div>
        </div>
    );
}
