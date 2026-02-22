import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from "@clerk/clerk-react";

const navItems = [
    { name: "Features", href: "#features" },
    { name: "Agents", href: "#agents" },
    { name: "Pricing", href: "#pricing" },
];

/** MoneyOps inline logo mark — matches the brand (green bg, zigzag + arrow) */
function MoneyOpsLogo({ size = 24 }) {
    return (
        <div
            className="flex items-center justify-center rounded-md bg-[#4CBB17] flex-shrink-0"
            style={{ width: size, height: size }}
        >
            <svg viewBox="0 0 32 32" width={size * 0.7} height={size * 0.7} fill="none">
                <path d="M10 22 L14 14 L18 18 L22 10" stroke="#000" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M19 10 L22 10 L22 13" stroke="#000" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
        </div>
    );
}

export default function Navigation() {
    const [isScrolled, setIsScrolled] = useState(false);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    useEffect(() => {
        const handleScroll = () => setIsScrolled(window.scrollY > 20);
        window.addEventListener("scroll", handleScroll);
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    return (
        <nav
            className={cn(
                "fixed top-0 left-0 right-0 z-50 transition-all duration-300 px-4",
                isScrolled
                    ? "bg-black/90 backdrop-blur-lg border-b border-[#2A2A2A] py-2"
                    : "bg-transparent py-4"
            )}
        >
            <div className="container mx-auto flex items-center justify-between">
                {/* Logo */}
                <a href="/" className="flex items-center space-x-2.5 group">
                    <MoneyOpsLogo size={32} />
                    <span className="text-xl font-bold text-white tracking-tight">
                        Money<span style={{ color: "#4CBB17" }}>Ops</span>
                    </span>
                </a>

                {/* Desktop Nav Links */}
                <div className="hidden md:flex items-center space-x-8">
                    {navItems.map((item) => (
                        <a
                            key={item.name}
                            href={item.href}
                            className="text-sm font-medium text-[#A0A0A0] hover:text-white transition-colors"
                        >
                            {item.name}
                        </a>
                    ))}
                </div>

                {/* Desktop CTA */}
                <div className="hidden md:flex items-center space-x-3">
                    <SignedOut>
                        <SignInButton mode="modal">
                            <button className="text-sm font-medium text-[#A0A0A0] hover:text-white transition-colors px-3 py-1.5">
                                Sign In
                            </button>
                        </SignInButton>
                        <SignUpButton mode="modal">
                            <button className="text-sm font-semibold bg-[#4CBB17] text-black px-4 py-1.5 rounded-lg hover:bg-[#3da314] transition-colors">
                                Get Started
                            </button>
                        </SignUpButton>
                    </SignedOut>
                    <SignedIn>
                        <Link to="/analytics">
                            <button className="text-sm font-semibold bg-[#4CBB17] text-black px-4 py-1.5 rounded-lg hover:bg-[#3da314] transition-colors">
                                Dashboard
                            </button>
                        </Link>
                        <UserButton afterSignOutUrl="/" />
                    </SignedIn>
                </div>

                {/* Mobile Hamburger */}
                <button
                    className="md:hidden p-2 text-white"
                    onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                    aria-label="Toggle menu"
                >
                    {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
                </button>
            </div>

            {/* Mobile Menu */}
            <AnimatePresence>
                {isMobileMenuOpen && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="md:hidden bg-black border-b border-[#2A2A2A] p-4 space-y-4"
                    >
                        {navItems.map((item) => (
                            <a
                                key={item.name}
                                href={item.href}
                                className="block text-[#A0A0A0] hover:text-white"
                                onClick={() => setIsMobileMenuOpen(false)}
                            >
                                {item.name}
                            </a>
                        ))}
                        <div className="flex flex-col gap-2 w-full pt-2">
                            <SignedOut>
                                <SignInButton mode="modal">
                                    <button className="w-full text-sm text-[#A0A0A0] border border-[#2A2A2A] rounded-lg py-2">Sign In</button>
                                </SignInButton>
                                <SignUpButton mode="modal">
                                    <button className="w-full text-sm font-semibold bg-[#4CBB17] text-black rounded-lg py-2">Get Started</button>
                                </SignUpButton>
                            </SignedOut>
                            <SignedIn>
                                <Link to="/analytics" className="w-full">
                                    <button className="w-full text-sm font-semibold bg-[#4CBB17] text-black rounded-lg py-2">Dashboard</button>
                                </Link>
                                <div className="flex justify-center">
                                    <UserButton afterSignOutUrl="/" />
                                </div>
                            </SignedIn>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </nav>
    );
}
