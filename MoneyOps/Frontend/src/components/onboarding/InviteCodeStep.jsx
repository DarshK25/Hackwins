import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

export function InviteCodeStep({ onNext, loading }) {
    const [inviteCode, setInviteCode] = useState("");
    const [verifying, setVerifying] = useState(false);
    const [verification, setVerification] = useState(null); // { valid, businessName?, error? }

    const handleVerify = async () => {
        if (!inviteCode.trim()) return;
        setVerifying(true);
        try {
            const response = await fetch("/api/onboarding/verify-invite", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: inviteCode }),
            });
            const data = await response.json();
            if (response.ok && data.valid) {
                setVerification({ valid: true, businessName: data.businessName });
            } else {
                setVerification({ valid: false, error: data.error || "Invalid code" });
            }
        } catch {
            setVerification({ valid: false, error: "Verification failed. Please try again." });
        } finally {
            setVerifying(false);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (verification?.valid) onNext({ inviteCode });
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-1">
                <h3 className="text-lg font-semibold">Join Your Team</h3>
                <p className="text-sm text-muted-foreground">
                    Enter the invite code shared by your admin.
                </p>
            </div>

            <div className="space-y-4">
                {/* Code Input + Verify */}
                <div className="space-y-2">
                    <Label htmlFor="inviteCode">Invite Code</Label>
                    <div className="flex gap-2">
                        <Input
                            id="inviteCode"
                            value={inviteCode}
                            onChange={(e) => {
                                setInviteCode(e.target.value.toUpperCase());
                                setVerification(null);
                            }}
                            placeholder="ABCD-1234-EFGH"
                            className="flex-1"
                        />
                        <Button
                            type="button"
                            onClick={handleVerify}
                            disabled={verifying || !inviteCode.trim()}
                        >
                            {verifying ? <Loader2 className="h-4 w-4 animate-spin" /> : "Verify"}
                        </Button>
                    </div>
                </div>

                {/* Verification Result */}
                {verification && (
                    <Alert variant={verification.valid ? "success" : "destructive"}>
                        <div className="flex items-start gap-2">
                            {verification.valid ? (
                                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600" />
                            ) : (
                                <XCircle className="h-4 w-4 mt-0.5" />
                            )}
                            <AlertDescription>
                                {verification.valid
                                    ? `✓ Valid code — you'll be joining: ${verification.businessName}`
                                    : verification.error}
                            </AlertDescription>
                        </div>
                    </Alert>
                )}
            </div>

            <div className="flex justify-end">
                <Button type="submit" disabled={!verification?.valid || loading}>
                    {loading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                        "Join Business →"
                    )}
                </Button>
            </div>
        </form>
    );
}
