import { useState } from "react";
import BudgetAnalysis from "@/components/BudgetAnalysis";
import ExpenseDashboard from "@/components/ExpenseDashboard";

const TABS = [
    { id: "expenses", label: "Expenses" },
    { id: "budgets", label: "Budget Analysis" },
];

export default function FinancesPage() {
    const [activeTab, setActiveTab] = useState("expenses");

    return (
        <div className="flex flex-col gap-6">
            <div className="rounded-2xl border border-[#222222] bg-[#111111] p-2">
                <div className="flex flex-wrap gap-2">
                    {TABS.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                                activeTab === tab.id
                                    ? "bg-[#4CBB17] text-black"
                                    : "text-[#A0A0A0] hover:bg-[#171717] hover:text-white"
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            {activeTab === "expenses" ? <ExpenseDashboard /> : <BudgetAnalysis />}
        </div>
    );
}
