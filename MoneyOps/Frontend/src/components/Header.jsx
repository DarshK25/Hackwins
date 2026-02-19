
import { Link } from "react-router-dom";
import { Moon, Sun, User } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export default function Header() {
    const { setTheme, theme } = useTheme();

    return (
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-16 items-center justify-between">
                <div className="flex items-center gap-2">
                    <Link to="/" className="flex items-center space-x-2">
                        <span className="font-bold text-xl">LedgerTalk</span>
                    </Link>
                </div>
                <div className="flex items-center gap-4">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                    >
                        <Sun className="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
                        <Moon className="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
                        <span className="sr-only">Toggle theme</span>
                    </Button>

                    <Link to="/settings">
                        <Avatar className="h-8 w-8 cursor-pointer hover:opacity-80 transition-opacity">
                            <AvatarImage src="" />
                            <AvatarFallback className="bg-primary/10 text-primary">
                                <User className="h-4 w-4" />
                            </AvatarFallback>
                        </Avatar>
                    </Link>
                </div>
            </div>
        </header>
    );
}
