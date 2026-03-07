import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import AnimatedTextCycle from "@/components/ui/animated-text-cycle";
import { Boxes } from "@/components/ui/background-boxes";
import { SlidingNumber } from "@/components/ui/sliding-number";

// Cycling words tuned to MoneyOps positioning
const CYCLE_WORDS = [
    "invoice creation",
    "cash flow",
    "compliance",
    "reconciliation",
    "tax filings",
    "payroll",
    "strategy & forecasting",
];

// Stat definitions — numeric value drives SlidingNumber, suffix is appended
const STATS = [
    { target: 12, suffix: "K+", label: "Invoices automated / mo" },
    { target: 94, suffix: "%", label: "Finance ops saved" },
    { target: 18, suffix: "h/wk", label: "Avg time saved" },
];

/** Counts from 0 → target over ~1.4 s with a ease-out curve */
function useCountUp(target, duration = 1400) {
    const [value, setValue] = useState(0);

    useEffect(() => {
        let start = null;
        const step = (ts) => {
            if (!start) start = ts;
            const progress = Math.min((ts - start) / duration, 1);
            // ease-out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            setValue(Math.round(eased * target));
            if (progress < 1) requestAnimationFrame(step);
        };
        // small delay so the page has loaded before counting starts
        const timer = setTimeout(() => requestAnimationFrame(step), 600);
        return () => clearTimeout(timer);
    }, [target, duration]);

    return value;
}

function AnimatedStat({ target, suffix, label }) {
    const value = useCountUp(target);

    return (
        <div className="text-center">
            <div
                className="text-3xl font-bold text-white flex items-baseline justify-center gap-0.5"
                style={{ fontVariantNumeric: "tabular-nums" }}
            >
                <SlidingNumber value={value} />
                <span>{suffix}</span>
            </div>
            <div className="text-xs mt-1" style={{ color: "#A0A0A0" }}>
                {label}
            </div>
        </div>
    );
}

export default function Hero() {
    return (
        <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16 bg-black">

            {/* ── Background Boxes layer ──────────────────────────────────── */}
            <div className="absolute inset-0 overflow-hidden z-0">
                <Boxes />
            </div>
            {/* Vignette mask */}
            <div
                className="absolute inset-0 w-full h-full z-10 pointer-events-none"
                style={{
                    background:
                        "radial-gradient(ellipse 75% 60% at 50% 50%, transparent 0%, #000 70%)",
                }}
            />

            {/* ── Content ─────────────────────────────────────────────────── */}
            <div className="relative z-20 container mx-auto text-center px-4">

                {/* Badge */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full mb-8"
                    style={{
                        backgroundColor: "#4CBB1715",
                        border: "1px solid #4CBB1730",
                    }}
                >
                    <span className="h-2 w-2 rounded-full bg-[#4CBB17] animate-pulse" />
                    <span className="text-sm font-medium" style={{ color: "#4CBB17" }}>
                        AI-Powered Invoicing
                    </span>
                </motion.div>

                {/* Main headline */}
                <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                    className="text-5xl md:text-7xl font-bold mb-5 tracking-tight text-white"
                >
                    Voice-To-Invoice{" "}
                    <br />
                    <span style={{ color: "#4CBB17" }}>under a minute</span>
                </motion.h1>

                {/* ── AnimatedTextCycle sub-headline ──────────────────────── */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.2 }}
                    className="flex items-center justify-center gap-2 text-2xl md:text-3xl font-light mb-6"
                    style={{ color: "#A0A0A0" }}
                >
                    <span>Automate your</span>
                    <AnimatedTextCycle
                        words={CYCLE_WORDS}
                        interval={2800}
                        className="text-white"
                    />
                </motion.div>

                {/* CTAs */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.4 }}
                    className="flex flex-wrap gap-4 justify-center mb-16"
                >
                    <Link to="/analytics">
                        <button
                            className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold transition-all hover:scale-105 hover:brightness-110"
                            style={{ backgroundColor: "#4CBB17", color: "#000" }}
                        >
                            Get Started Free <ArrowRight className="w-4 h-4" />
                        </button>
                    </Link>
                </motion.div>

                {/* ── Animated Stats ───────────────────────────────────────── */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.5 }}
                    className="flex flex-wrap justify-center gap-8 md:gap-16 mb-16"
                >
                    {STATS.map((stat) => (
                        <AnimatedStat key={stat.label} {...stat} />
                    ))}
                </motion.div>

                {/* Dashboard preview card */}
                <motion.div
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.65 }}
                    className="mx-auto max-w-2xl rounded-2xl p-6 text-left"
                    style={{
                        backgroundColor: "#0D0D0D",
                        border: "1px solid #2A2A2A",
                        boxShadow: "0 0 80px #4CBB1712",
                    }}
                >
                    {/* Fake traffic-light bar */}
                    <div className="flex items-center gap-2 mb-4">
                        <span className="h-3 w-3 rounded-full bg-[#CD1C18]" />
                        <span className="h-3 w-3 rounded-full bg-[#FFB300]" />
                        <span className="h-3 w-3 rounded-full bg-[#4CBB17]" />
                        <span className="ml-auto text-xs" style={{ color: "#A0A0A0" }}>
                            MoneyOps Dashboard
                        </span>
                    </div>
                    {/* KPI cards */}
                    <div className="grid grid-cols-3 gap-3 mb-4">
                        {[
                            { label: "Revenue", val: "₹52L", up: true },
                            { label: "Cash Flow", val: "₹12L", up: true },
                            { label: "Overdue", val: "₹1.8L", up: false },
                        ].map((card) => (
                            <div
                                key={card.label}
                                className="rounded-xl p-3"
                                style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A" }}
                            >
                                <div className="text-xs mb-1" style={{ color: "#A0A0A0" }}>
                                    {card.label}
                                </div>
                                <div className="text-lg font-bold text-white">{card.val}</div>
                                <div
                                    className="text-xs mt-0.5 font-medium"
                                    style={{ color: card.up ? "#4CBB17" : "#CD1C18" }}
                                >
                                    {card.up ? "▲ 12%" : "▼ 3%"}
                                </div>
                            </div>
                        ))}
                    </div>
                    {/* Fake sparkline bar chart */}
                    <div className="flex items-end gap-1.5 h-16">
                        {[40, 55, 45, 70, 60, 80, 65, 90, 75, 85, 72, 95].map((h, i, arr) => (
                            <div
                                key={i}
                                className="flex-1 rounded-t transition-all"
                                style={{
                                    height: `${h}%`,
                                    backgroundColor:
                                        i === arr.length - 1 ? "#4CBB17" : i === arr.length - 2 ? "#4CBB1760" : "#2A2A2A",
                                }}
                            />
                        ))}
                    </div>
                </motion.div>
            </div>
        </section>
    );
}
