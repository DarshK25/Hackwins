import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from "@clerk/clerk-react";

const navItems = [
    { name: "Features", href: "#features" },
    { name: "Agents", href: "#agents" },
    { name: "Pricing", href: "#pricing" },
];

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
                    ? "bg-white/80 backdrop-blur-lg border-b border-slate-200 py-2"
                    : "bg-transparent py-4"
            )}
        >
            <div className="container mx-auto flex items-center justify-between">
                {/* Logo */}
                <a href="/" className="flex items-center space-x-2 group">
                    <Sparkles className="w-6 h-6 text-blue-600 group-hover:rotate-12 transition-transform" />
                    <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
                        LedgerTalk
                    </span>
                </a>

                {/* Desktop Nav Links */}
                <div className="hidden md:flex items-center space-x-8">
                    {navItems.map((item) => (
                        <a
                            key={item.name}
                            href={item.href}
                            className="text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors"
                        >
                            {item.name}
                        </a>
                    ))}
                </div>

                {/* Desktop CTA - Clerk auth */}
                <div className="hidden md:flex items-center space-x-4">
                    <SignedOut>
                        <SignInButton mode="modal">
                            <Button variant="ghost">Sign In</Button>
                        </SignInButton>
                        <SignUpButton mode="modal">
                            <Button>Get Started</Button>
                        </SignUpButton>
                    </SignedOut>
                    <SignedIn>
                        <Link to="/analytics">
                            <Button variant="outline">Dashboard</Button>
                        </Link>
                        <UserButton afterSignOutUrl="/" />
                    </SignedIn>
                </div>

                {/* Mobile Hamburger */}
                <button
                    className="md:hidden p-2"
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
                        className="md:hidden bg-white border-b border-slate-200 p-4 space-y-4"
                    >
                        {navItems.map((item) => (
                            <a
                                key={item.name}
                                href={item.href}
                                className="block text-slate-600 hover:text-blue-600"
                                onClick={() => setIsMobileMenuOpen(false)}
                            >
                                {item.name}
                            </a>
                        ))}
                        <div className="flex flex-col gap-2 w-full">
                            <SignedOut>
                                <SignInButton mode="modal">
                                    <Button variant="ghost" className="w-full">Sign In</Button>
                                </SignInButton>
                                <SignUpButton mode="modal">
                                    <Button className="w-full">Get Started</Button>
                                </SignUpButton>
                            </SignedOut>
                            <SignedIn>
                                <Link to="/analytics" className="w-full">
                                    <Button className="w-full">Dashboard</Button>
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
