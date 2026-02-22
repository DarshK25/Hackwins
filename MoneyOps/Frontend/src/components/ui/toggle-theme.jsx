import React from "react";
import { MonitorCog, Sun, MoonStar } from "lucide-react";
import { motion } from "framer-motion";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";

const THEME_OPTIONS = [
    { icon: MonitorCog, value: "system", label: "System" },
    { icon: Sun, value: "light", label: "Light" },
    { icon: MoonStar, value: "dark", label: "Dark" },
];

export function ToggleTheme({ className }) {
    const { theme, setTheme } = useTheme();
    const [isMounted, setIsMounted] = React.useState(false);

    React.useEffect(() => { setIsMounted(true); }, []);

    if (!isMounted) {
        return <div className="flex h-8 w-[88px]" />;
    }

    return (
        <motion.div
            key="theme-toggle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            className={cn(
                "inline-flex items-center overflow-hidden rounded-lg gap-0.5 p-0.5",
                className
            )}
            style={{
                backgroundColor: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.1)",
                backdropFilter: "blur(8px)",
            }}
            role="radiogroup"
            aria-label="Select theme"
        >
            {THEME_OPTIONS.map((option) => {
                const isActive = theme === option.value;
                return (
                    <button
                        key={option.value}
                        className={cn(
                            "relative flex h-7 w-7 cursor-pointer items-center justify-center rounded-md transition-colors duration-200 outline-none",
                            isActive
                                ? "text-black"
                                : "text-[#A0A0A0] hover:text-white"
                        )}
                        role="radio"
                        aria-checked={isActive}
                        aria-label={`Switch to ${option.label} theme`}
                        onClick={() => setTheme(option.value)}
                        title={option.label}
                    >
                        {isActive && (
                            <motion.div
                                layoutId="theme-active-pill"
                                transition={{ type: "spring", bounce: 0.15, duration: 0.5 }}
                                className="absolute inset-0 rounded-md"
                                style={{ backgroundColor: "#4CBB17" }}
                            />
                        )}
                        <option.icon className="relative z-10 h-3.5 w-3.5" />
                    </button>
                );
            })}
        </motion.div>
    );
}
