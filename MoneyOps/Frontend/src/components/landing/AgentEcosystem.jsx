import { motion } from "framer-motion";

const agents = [
    { name: "Finance Agent", role: "Manages accounting, invoices, and payroll", dot: "#4CBB17" },
    { name: "Cashflow Agent", role: "Predicts liquidity and optimizes spend", dot: "#60A5FA" },
    { name: "Research Agent", role: "Tracks competitors and market movements", dot: "#A78BFA" },
    { name: "Sales Agent", role: "Analyzes deals and revenue forecasts", dot: "#4CBB17" },
    { name: "Compliance Agent", role: "Ensures tax and GST compliance", dot: "#FFB300" },
    { name: "Alert Agent", role: "Sends priority alerts on KPIs", dot: "#CD1C18" },
];

export default function AgentEcosystem() {
    return (
        <section id="agents" className="py-24 bg-black">
            <div className="container mx-auto px-4 text-center">
                <h2 className="text-4xl font-bold mb-4 text-white">
                    Agent <span style={{ color: "#4CBB17" }}>Ecosystem</span>
                </h2>
                <p className="mb-12 text-sm" style={{ color: "#A0A0A0" }}>
                    Six specialized AI agents working in concert to run your financial operations.
                </p>

                <div className="grid md:grid-cols-3 gap-5">
                    {agents.map((agent, i) => (
                        <motion.div
                            key={i}
                            whileHover={{ y: -3, borderColor: agent.dot }}
                            transition={{ type: "spring", stiffness: 300 }}
                            className="p-5 rounded-xl text-left transition-all"
                            style={{
                                backgroundColor: "#111111",
                                border: "1px solid #2A2A2A",
                            }}
                        >
                            <div
                                className="w-2.5 h-2.5 rounded-full mb-3"
                                style={{ backgroundColor: agent.dot }}
                            />
                            <h3 className="font-bold text-base text-white">{agent.name}</h3>
                            <p className="text-sm mt-1" style={{ color: "#A0A0A0" }}>{agent.role}</p>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}
