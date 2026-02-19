import { cn } from "@/lib/utils";

const agents = [
    {
        name: "Finance Agent",
        role: "Manages accounting, invoices, and payroll",
        color: "bg-blue-500",
    },
    {
        name: "Cashflow Agent",
        role: "Predicts liquidity and optimizes spend",
        color: "bg-cyan-500",
    },
    {
        name: "Research Agent",
        role: "Tracks competitors and market movements",
        color: "bg-purple-500",
    },
    {
        name: "Sales Agent",
        role: "Analyzes deals and revenue forecasts",
        color: "bg-green-500",
    },
    {
        name: "Compliance Agent",
        role: "Ensures tax and GST compliance",
        color: "bg-orange-500",
    },
    {
        name: "Alert Agent",
        role: "Sends priority alerts on KPIs",
        color: "bg-red-500",
    },
];

export default function AgentEcosystem() {
    return (
        <section id="agents" className="py-24">
            <div className="container mx-auto px-4 text-center">
                <h2 className="text-4xl font-bold mb-12">
                    Agent <span className="text-blue-600">Ecosystem</span>
                </h2>

                <div className="grid md:grid-cols-3 gap-6">
                    {agents.map((agent, i) => (
                        <div
                            key={i}
                            className="p-6 border border-slate-100 rounded-xl text-left bg-white shadow-sm hover:shadow-md transition-shadow"
                        >
                            <div className={cn("w-3 h-3 rounded-full mb-4", agent.color)} />
                            <h3 className="font-bold text-lg">{agent.name}</h3>
                            <p className="text-sm text-slate-500 mt-1">{agent.role}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
