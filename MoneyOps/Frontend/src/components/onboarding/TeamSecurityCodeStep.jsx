import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Lock, CheckCircle2, Info } from "lucide-react";

export function TeamSecurityCodeStep({ mode = "new-business", onNext, onBack, loading, businessName }) {
    const [securityCode, setSecurityCode] = useState("");
    const [confirmCode, setConfirmCode] = useState("");
    const [error, setError] = useState("");
    const [submitted, setSubmitted] = useState(false);

    const isNewBusiness = mode === "new-business";
    const isJoiningBusiness = mode === "join-business";

    const handleSubmit = (e) => {
        e.preventDefault();
        setError("");

        // Validation
        if (!securityCode.trim()) {
            setError(isNewBusiness ? "Please set a security code" : "Please enter the security code");
            return;
        }

        if (securityCode.length < 4) {
            setError("Security code must be at least 4 characters");
            return;
        }

        if (isNewBusiness && securityCode !== confirmCode) {
            setError("Codes don't match. Please try again.");
            return;
        }

        setSubmitted(true);
        onNext({ teamActionCode: securityCode });
    };

    if (isNewBusiness) {
        return (
            <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-1">
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Lock className="h-5 w-5 text-[#4CBB17]" />
                        Set Team Security Code
                    </h3>
                    <p className="text-sm text-muted-foreground">
                        Create a shared code that all team members will need to create invoices and add clients.
                    </p>
                </div>

                {/* Info Alert */}
                <Alert style={{ backgroundColor: "#4CBB1715", border: "1px solid #4CBB1740" }}>
                    <Info className="h-4 w-4 text-[#4CBB17]" />
                    <AlertDescription className="text-[#A0A0A0]">
                        This code will be shared with team members via email when they're invited. Make it secure but memorable.
                    </AlertDescription>
                </Alert>

                {/* New Code Input */}
                <div className="space-y-2">
                    <Label htmlFor="securityCode">Team Security Code *</Label>
                    <Input
                        id="securityCode"
                        type="password"
                        value={securityCode}
                        onChange={(e) => {
                            setSecurityCode(e.target.value);
                            setError("");
                        }}
                        placeholder="Enter a code (min 4 characters)"
                        disabled={loading}
                        className="text-white placeholder-[#A0A0A0]"
                        style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                    />
                    <p className="text-xs text-[#A0A0A0]">
                        {securityCode.length} character{securityCode.length !== 1 ? "s" : ""} • Min 4 required
                    </p>
                </div>

                {/* Confirm Code Input */}
                <div className="space-y-2">
                    <Label htmlFor="confirmCode">Confirm Code *</Label>
                    <Input
                        id="confirmCode"
                        type="password"
                        value={confirmCode}
                        onChange={(e) => {
                            setConfirmCode(e.target.value);
                            setError("");
                        }}
                        placeholder="Re-enter the code to confirm"
                        disabled={loading}
                        className="text-white placeholder-[#A0A0A0]"
                        style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                    />
                </div>

                {/* Match indicator */}
                {securityCode && confirmCode && (
                    <div className="flex items-center gap-2">
                        {securityCode === confirmCode ? (
                            <>
                                <CheckCircle2 className="h-5 w-5 text-[#4CBB17]" />
                                <span className="text-sm text-[#4CBB17]">Codes match ✓</span>
                            </>
                        ) : (
                            <>
                                <div className="h-5 w-5 rounded-full border-2 border-red-500" />
                                <span className="text-sm text-red-500">Codes don't match</span>
                            </>
                        )}
                    </div>
                )}

                {/* Error */}
                {error && (
                    <Alert variant="destructive">
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                {/* Buttons */}
                <div className="flex gap-3">
                    <Button
                        type="button"
                        variant="outline"
                        onClick={onBack}
                        disabled={loading}
                        className="text-white border-[#2A2A2A] hover:bg-[#2A2A2A]"
                    >
                        Back
                    </Button>
                    <Button
                        type="submit"
                        disabled={
                            loading ||
                            !securityCode.trim() ||
                            securityCode.length < 4 ||
                            securityCode !== confirmCode
                        }
                        className="flex-1"
                        style={{ backgroundColor: "#4CBB17", color: "#000000" }}
                    >
                        {loading ? (
                            <>
                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                Setting up...
                            </>
                        ) : (
                            "Continue"
                        )}
                    </Button>
                </div>
            </form>
        );
    }

    // Join business mode - enter existing code
    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-1">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Lock className="h-5 w-5 text-[#4CBB17]" />
                    Enter Team Security Code
                </h3>
                <p className="text-sm text-muted-foreground">
                    {businessName && `You're joining ${businessName}. `}
                    Enter the security code that was shared with you via email.
                </p>
            </div>

            {/* Info Alert */}
            <Alert style={{ backgroundColor: "#4CBB1715", border: "1px solid #4CBB1740" }}>
                <Info className="h-4 w-4 text-[#4CBB17]" />
                <AlertDescription className="text-[#A0A0A0]">
                    This code is required to create invoices and add clients. You'll need it for all team actions.
                </AlertDescription>
            </Alert>

            {/* Code Input */}
            <div className="space-y-2">
                <Label htmlFor="securityCode">Team Security Code *</Label>
                <Input
                    id="securityCode"
                    type="password"
                    value={securityCode}
                    onChange={(e) => {
                        setSecurityCode(e.target.value);
                        setError("");
                    }}
                    placeholder="Enter the security code"
                    disabled={loading}
                    className="text-white placeholder-[#A0A0A0]"
                    style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                    autoComplete="off"
                />
            </div>

            {/* Error */}
            {error && (
                <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {/* Buttons */}
            <div className="flex gap-3">
                <Button
                    type="button"
                    variant="outline"
                    onClick={onBack}
                    disabled={loading}
                    className="text-white border-[#2A2A2A] hover:bg-[#2A2A2A]"
                >
                    Back
                </Button>
                <Button
                    type="submit"
                    disabled={loading || !securityCode.trim() || securityCode.length < 4}
                    className="flex-1"
                    style={{ backgroundColor: "#4CBB17", color: "#000000" }}
                >
                    {loading ? (
                        <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Verifying...
                        </>
                    ) : (
                        "Continue"
                    )}
                </Button>
            </div>
        </form>
    );
}
