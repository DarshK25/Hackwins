import { Check } from "lucide-react";
import { Link } from "react-router-dom";

const plans = [
    {
        name: "Pro",
        price: "$29",
        period: "/ month",
        features: ["Core AI agents", "1,000 transactions/mo", "Email support", "API access"],
        popular: false,
    },
    {
        name: "Growth",
        price: "$79",
        period: "/ month",
        features: ["All Pro features", "Cashflow automation", "10,000 transactions/mo", "Priority support"],
        popular: true,
    },
    {
        name: "Enterprise",
        price: "Custom",
        period: "",
        features: ["SLA guarantee", "Custom integrations", "Dedicated Account Manager", "On-premise option"],
        popular: false,
    },
];

export default function Pricing() {
    return (
        <section id="pricing" className="py-24" style={{ backgroundColor: "#0A0A0A" }}>
            <div className="container mx-auto px-4">
                <div className="text-center mb-16">
                    <h2 className="text-4xl font-bold mb-4 text-white">
                        Simple <span style={{ color: "#4CBB17" }}>Pricing</span>
                    </h2>
                    <p style={{ color: "#A0A0A0" }}>Start free. Scale as you grow.</p>
                </div>

                <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
                    {plans.map((plan, i) => (
                        <div
                            key={i}
                            className="p-8 rounded-2xl transition-all"
                            style={{
                                backgroundColor: "#111111",
                                border: plan.popular ? "1px solid #4CBB17" : "1px solid #2A2A2A",
                                transform: plan.popular ? "scale(1.04)" : "scale(1)",
                                boxShadow: plan.popular ? "0 0 40px #4CBB1718" : "none",
                            }}
                        >
                            {plan.popular && (
                                <span
                                    className="inline-block text-xs font-semibold px-3 py-1 rounded-full mb-4"
                                    style={{ backgroundColor: "#4CBB1720", color: "#4CBB17", border: "1px solid #4CBB1740" }}
                                >
                                    Most Popular
                                </span>
                            )}
                            <h3 className="text-xl font-bold text-white">{plan.name}</h3>
                            <div className="my-4">
                                <span className="text-4xl font-bold text-white">{plan.price}</span>
                                {plan.period && (
                                    <span className="text-sm ml-1" style={{ color: "#A0A0A0" }}>{plan.period}</span>
                                )}
                            </div>

                            <ul className="space-y-3 mb-8">
                                {plan.features.map((feat) => (
                                    <li key={feat} className="flex items-center text-sm" style={{ color: "#A0A0A0" }}>
                                        <Check className="w-4 h-4 mr-2 flex-shrink-0" style={{ color: "#4CBB17" }} />
                                        {feat}
                                    </li>
                                ))}
                            </ul>

                            <Link to="/analytics" className="w-full block">
                                <button
                                    className="w-full py-2.5 rounded-xl text-sm font-semibold transition-all"
                                    style={
                                        plan.popular
                                            ? { backgroundColor: "#4CBB17", color: "#000" }
                                            : { backgroundColor: "transparent", color: "#A0A0A0", border: "1px solid #2A2A2A" }
                                    }
                                    onMouseEnter={(e) => {
                                        if (!plan.popular) {
                                            e.currentTarget.style.borderColor = "#4CBB17";
                                            e.currentTarget.style.color = "#4CBB17";
                                        }
                                    }}
                                    onMouseLeave={(e) => {
                                        if (!plan.popular) {
                                            e.currentTarget.style.borderColor = "#2A2A2A";
                                            e.currentTarget.style.color = "#A0A0A0";
                                        }
                                    }}
                                >
                                    Get Started
                                </button>
                            </Link>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
