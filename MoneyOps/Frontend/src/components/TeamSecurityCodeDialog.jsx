import { useEffect, useState } from "react";
import { ShieldAlert } from "lucide-react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";

export default function TeamSecurityCodeDialog({
    open,
    attempts = 0,
    onClose,
    onSubmit,
}) {
    const [code, setCode] = useState("");

    useEffect(() => {
        if (open) {
            setCode("");
        }
    }, [open, attempts]);

    const isRetry = attempts > 0;

    const handleSubmit = (event) => {
        event.preventDefault();
        const trimmedCode = code.trim();
        if (!trimmedCode) {
            return;
        }
        onSubmit?.(trimmedCode);
    };

    return (
        <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose?.()}>
            <DialogContent className="border-[#2A2A2A] bg-[#111111] text-white sm:max-w-md">
                <DialogHeader>
                    <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl border border-[#2A2A2A] bg-[#171717]">
                        <ShieldAlert className={`h-5 w-5 ${isRetry ? "text-[#FFB300]" : "text-[#4CBB17]"}`} />
                    </div>
                    <DialogTitle className="text-xl">
                        {isRetry ? "Incorrect Code" : "Team Security Code"}
                    </DialogTitle>
                    <DialogDescription className="text-[#A0A0A0]">
                        {isRetry
                            ? "That code did not match. Enter it once more to send this invoice."
                            : "Enter the team security code to email this invoice."}
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="rounded-2xl border border-[#2A2A2A] bg-[#151515] p-4">
                        <label htmlFor="team-security-code" className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-[#A0A0A0]">
                            Verification
                        </label>
                        <input
                            id="team-security-code"
                            type="password"
                            value={code}
                            onChange={(event) => setCode(event.target.value)}
                            placeholder="Enter team security code"
                            autoFocus
                            className="w-full rounded-xl border border-[#2A2A2A] bg-[#0F0F0F] px-4 py-3 text-sm text-white outline-none transition focus:border-[#4CBB17]"
                        />
                        <p className="mt-2 text-xs text-[#6F6F6F]">
                            This protects invoice sending for your workspace.
                        </p>
                    </div>

                    <DialogFooter className="gap-2 sm:justify-end">
                        <button
                            type="button"
                            onClick={() => onClose?.()}
                            className="mo-btn-secondary"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={!code.trim()}
                            className="mo-btn-primary disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            Send Invoice
                        </button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
