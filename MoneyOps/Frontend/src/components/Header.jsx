import { Link } from "react-router-dom";
import { User } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export default function Header() {
    return (
        <header className="sticky top-0 z-50 w-full" style={{ backgroundColor: "#111111", borderBottom: "1px solid #2A2A2A" }}>
            <div className="container flex h-14 items-center justify-between">
                <Link to="/" className="flex items-center gap-2">
                    <div className="h-7 w-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: "#4CBB17" }}>
                        <span className="text-black font-bold text-sm">M</span>
                    </div>
                    <span className="font-bold text-lg text-white">MoneyOps</span>
                </Link>
                <div className="flex items-center gap-3">
                    <Link to="/settings">
                        <Avatar className="h-8 w-8 cursor-pointer hover:opacity-80 transition-opacity">
                            <AvatarImage src="" />
                            <AvatarFallback style={{ backgroundColor: "#4CBB1720", color: "#4CBB17" }}>
                                <User className="h-4 w-4" />
                            </AvatarFallback>
                        </Avatar>
                    </Link>
                </div>
            </div>
        </header>
    );
}
