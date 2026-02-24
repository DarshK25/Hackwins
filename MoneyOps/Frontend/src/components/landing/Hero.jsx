import { motion } from "framer-motion";
import { ArrowRight, Zap } from "lucide-react";
import { Link } from "react-router-dom";
import AnimatedTextCycle from "@/components/ui/animated-text-cycle";
import { Boxes } from "@/components/ui/background-boxes";

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

const stats = [
    { label: "Invoices automated / mo", value: "12K+" },
    { label: "Finance ops saved", value: "94%" },
    { label: "Avg time saved", value: "18h/wk" },
];

export default function Hero() {
    return (
        <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16 bg-black">

            {/* ── Background Boxes layer ──────────────────────────────────── */}
            {/* Vignette mask so grid fades gracefully into the content */}
            <div
                className="absolute inset-0 w-full h-full z-10 pointer-events-none"
                style={{
                    background:
                        "radial-gradient(ellipse 75% 60% at 50% 50%, transparent 0%, #000 70%)",
                }}
            />
            {/* Grid boxes — lower z so the mask sits on top */}
            <div className="absolute inset-0 overflow-hidden z-0">
                <Boxes rows={55} cols={35} />
            </div>

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
                        AI-Powered Finance OS
                    </span>
                </motion.div>

                {/* Main headline */}
                <motion.h1
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                    className="text-5xl md:text-7xl font-bold mb-5 tracking-tight text-white"
                >
                    Your Business{" "}
                    <br />
                    <span style={{ color: "#4CBB17" }}>Financially Autonomous</span>
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

                {/* Body copy */}
                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.3 }}
                    className="text-base max-w-xl mx-auto mb-10"
                    style={{ color: "#6A6A6A" }}
                >
                </motion.p>

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
                    <Link to="/analytics">
                        <button
                            className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium transition-all"
                            style={{
                                border: "1px solid #2A2A2A",
                                color: "#A0A0A0",
                                backgroundColor: "transparent",
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = "#4CBB17";
                                e.currentTarget.style.color = "#4CBB17";
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = "#2A2A2A";
                                e.currentTarget.style.color = "#A0A0A0";
                            }}
                        >
                            <Zap className="w-4 h-4" />
                            Try AI Assistant
                        </button>
                    </Link>
                </motion.div>

                {/* Stats */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.5 }}
                    className="flex flex-wrap justify-center gap-8 md:gap-16 mb-16"
                >
                    {stats.map((stat, i) => (
                        <div key={i} className="text-center">
                            <div className="text-3xl font-bold text-white">{stat.value}</div>
                            <div className="text-xs mt-1" style={{ color: "#A0A0A0" }}>
                                {stat.label}
                            </div>
                        </div>
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
