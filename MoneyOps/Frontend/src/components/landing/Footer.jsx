import { Sparkles } from "lucide-react";

export default function Footer() {
    return (
        <footer className="py-12 border-t border-slate-200 text-center">
            <div className="flex justify-center items-center gap-2 mb-4 font-bold text-blue-600">
                <Sparkles className="w-5 h-5" />
                LedgerTalk
            </div>
            <p className="text-slate-400 text-sm">
                © {new Date().getFullYear()} LedgerTalk. All rights reserved.
            </p>
        </footer>
    );
}
