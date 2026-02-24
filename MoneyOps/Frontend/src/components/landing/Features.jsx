import { motion } from "framer-motion";
import { Bot, TrendingUp, Search, DollarSign, Shield, Bell } from "lucide-react";

const features = [
    {
        icon: Bot,
        title: "Autonomous Reconciliation",
        description: "Detects and fixes mismatched invoices automatically.",
        color: "#4CBB17",
    },
    {
        icon: TrendingUp,
        title: "Cashflow Forecasting",
        description: "Predicts 30–90 day liquidity trends with data-driven insights.",
        color: "#60A5FA",
    },
    {
        icon: Search,
        title: "Market Intelligence",
        description: "Monitors market updates via autonomous research agents.",
        color: "#A78BFA",
    },
    {
        icon: DollarSign,
        title: "Auto-Invoicing",
        description: "Generates, sends, and follows up on invoices automatically.",
        color: "#4CBB17",
    },
    {
        icon: Shield,
        title: "Compliance Tracking",
        description: "Ensures timely tax, GST, and statutory compliance.",
        color: "#FFB300",
    },
    {
        icon: Bell,
        title: "Real-Time Alerts",
        description: "Actionable KPI triggers and live business insights.",
        color: "#CD1C18",
    },
];

export default function Features() {
    return (
        <section id="features" className="py-24" style={{ backgroundColor: "#0A0A0A" }}>
            <div className="container mx-auto px-4">
                {/* Section heading */}
                <div className="text-center mb-16">
                    <h2 className="text-4xl font-bold mb-4 text-white">
                        What Makes It <span style={{ color: "#4CBB17" }}>Different</span>
                    </h2>
                    <p style={{ color: "#A0A0A0" }}>Action-oriented AI that executes — not just talks.</p>
                </div>

                {/* Feature cards */}
                <div className="grid md:grid-cols-3 gap-6">
                    {features.map((feature, i) => (
                        <motion.div
                            key={i}
                            whileHover={{ y: -4 }}
                            transition={{ type: "spring", stiffness: 300 }}
                            className="p-6 rounded-2xl text-left"
                            style={{
                                backgroundColor: "#111111",
                                border: "1px solid #2A2A2A",
                            }}
                        >
                            <div
                                className="w-10 h-10 rounded-xl flex items-center justify-center mb-4"
                                style={{ backgroundColor: `${feature.color}18`, border: `1px solid ${feature.color}30` }}
                            >
                                <feature.icon className="w-5 h-5" style={{ color: feature.color }} />
                            </div>
                            <h3 className="text-lg font-bold mb-2 text-white">{feature.title}</h3>
                            <p className="text-sm" style={{ color: "#A0A0A0" }}>{feature.description}</p>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}
