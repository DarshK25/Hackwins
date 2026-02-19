import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Link } from "react-router-dom";

const plans = [
    {
        name: "Pro",
        price: "$29",
        features: ["Core agents", "1,000 tx/mo", "Email support"],
        popular: false,
    },
    {
        name: "Growth",
        price: "$79",
        features: ["All Pro", "Cashflow automation", "10,000 tx/mo"],
        popular: true,
    },
    {
        name: "Enterprise",
        price: "Custom",
        features: ["SLA guarantee", "Custom integrations", "Account Manager"],
        popular: false,
    },
];

export default function Pricing() {
    return (
        <section id="pricing" className="py-24 bg-slate-50">
            <div className="container mx-auto px-4">
                <div className="text-center mb-16">
                    <h2 className="text-4xl font-bold mb-4">
                        Simple <span className="text-blue-600">Pricing</span>
                    </h2>
                    <p className="text-slate-600">Start free. Scale as you grow.</p>
                </div>

                <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
                    {plans.map((plan, i) => (
                        <div
                            key={i}
                            className={cn(
                                "p-8 rounded-2xl border bg-white transition-all",
                                plan.popular
                                    ? "border-blue-600 ring-4 ring-blue-600/5 scale-105 shadow-lg"
                                    : "border-slate-200 shadow-sm"
                            )}
                        >
                            {plan.popular && (
                                <span className="inline-block text-xs font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full mb-4">
                                    Most Popular
                                </span>
                            )}
                            <h3 className="text-xl font-bold">{plan.name}</h3>
                            <div className="text-4xl font-bold my-4">{plan.price}</div>

                            <ul className="space-y-3 mb-8">
                                {plan.features.map((feat) => (
                                    <li key={feat} className="flex items-center text-sm text-slate-600">
                                        <Check className="w-4 h-4 text-blue-600 mr-2 flex-shrink-0" />
                                        {feat}
                                    </li>
                                ))}
                            </ul>

                            <Link to="/analytics" className="w-full">
                                <Button className="w-full" variant={plan.popular ? "default" : "outline"}>
                                    Get Started
                                </Button>
                            </Link>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
