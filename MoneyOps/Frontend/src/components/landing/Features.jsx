import { motion } from "framer-motion";
import { Bot, TrendingUp, Search, DollarSign, Shield, Bell } from "lucide-react";
import { cn } from "@/lib/utils";

const features = [
    {
        icon: Bot,
        title: "Autonomous Reconciliation",
        description: "Detects and fixes mismatched invoices automatically.",
        color: "text-blue-500",
    },
    {
        icon: TrendingUp,
        title: "Cashflow Forecasting",
        description: "Predicts 30-90 day liquidity trends with data-driven insights.",
        color: "text-cyan-500",
    },
    {
        icon: Search,
        title: "Market Intelligence",
        description: "Monitors market updates via research agents.",
        color: "text-purple-500",
    },
    {
        icon: DollarSign,
        title: "Auto-Invoicing",
        description: "Generates, sends, and follows up invoices.",
        color: "text-green-500",
    },
    {
        icon: Shield,
        title: "Compliance Tracking",
        description: "Ensures timely tax, GST, and statutory compliance.",
        color: "text-orange-500",
    },
    {
        icon: Bell,
        title: "Real-Time Alerts",
        description: "Actionable KPIs and triggers business insights live.",
        color: "text-red-500",
    },
];

export default function Features() {
    return (
        <section id="features" className="py-24 bg-slate-50">
            <div className="container mx-auto px-4">
                {/* Section heading */}
                <div className="text-center mb-16">
                    <h2 className="text-4xl font-bold mb-4">
                        What Makes It <span className="text-blue-600">Different</span>
                    </h2>
                    <p className="text-slate-600">Action-oriented AI that executes—not just talks.</p>
                </div>

                {/* Feature cards */}
                <div className="grid md:grid-cols-3 gap-8">
                    {features.map((feature, i) => (
                        <motion.div
                            key={i}
                            whileHover={{ y: -5 }}
                            transition={{ type: "spring", stiffness: 300 }}
                            className="p-8 bg-white rounded-2xl shadow-sm border border-slate-100"
                        >
                            <feature.icon className={cn("w-10 h-10 mb-4", feature.color)} />
                            <h3 className="text-xl font-bold mb-2">{feature.title}</h3>
                            <p className="text-slate-600 text-sm">{feature.description}</p>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}
