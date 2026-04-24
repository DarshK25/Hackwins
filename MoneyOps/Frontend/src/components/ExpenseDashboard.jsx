import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth, useUser } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { toast } from "sonner";
import {
    AlertCircle,
    Loader2,
    Pencil,
    Plus,
    RefreshCw,
    Tag,
    Trash2,
    Wallet,
} from "lucide-react";
import {
    Cell,
    Legend,
    Line,
    LineChart,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import ExpenseInsightsPanel from "@/components/ExpenseInsightsPanel";
import { getTeamSecurityAttemptState } from "@/lib/teamSecurityAttempts";

const DEFAULT_CATEGORIES = ["Office", "Marketing", "Salaries", "Utilities", "Travel", "Software", "Hardware", "Legal", "Taxes", "Other"];
const CHART_COLORS = ["#4CBB17", "#60A5FA", "#FFB300", "#F87171", "#34D399", "#A78BFA", "#F97316", "#2DD4BF"];

const EMPTY_FORM = {
    id: "",
    amount: "",
    category: "Office",
    description: "",
    date: new Date().toISOString().slice(0, 10),
    paymentMethod: "",
    receiptUrl: "",
    teamActionCode: "",
};

function formatMoney(value) {
    return `Rs ${Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function parseApiPayload(payload) {
    return payload?.data ?? payload;
}

function ModalShell({ title, onClose, children }) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
            <div className="w-full max-w-2xl rounded-2xl border border-[#2A2A2A] bg-[#0F0F0F] p-6 shadow-2xl">
                <div className="flex items-center justify-between gap-3">
                    <h3 className="text-lg font-semibold text-white">{title}</h3>
                    <button onClick={onClose} className="rounded-lg border border-[#2A2A2A] px-3 py-1 text-sm text-[#A0A0A0] hover:text-white">
                        Close
                    </button>
                </div>
                <div className="mt-5">{children}</div>
            </div>
        </div>
    );
}

export default function ExpenseDashboard() {
    const { getToken } = useAuth();
    const { user } = useUser();
    const { loading: onboardingLoading, userId, orgId } = useOnboardingStatus();

    const [summary, setSummary] = useState(null);
    const [expensePage, setExpensePage] = useState({
        content: [],
        pageNumber: 0,
        totalPages: 0,
        totalElements: 0,
        first: true,
        last: true,
    });
    const [categories, setCategories] = useState(DEFAULT_CATEGORIES);
    const [customCategories, setCustomCategories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState("");
    const [period, setPeriod] = useState("monthly");
    const [pageNumber, setPageNumber] = useState(0);
    const [filters, setFilters] = useState({
        category: "ALL",
        dateFrom: "",
        dateTo: "",
        amountMin: "",
        amountMax: "",
    });
    const [expenseForm, setExpenseForm] = useState(EMPTY_FORM);
    const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
    const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
    const [newCategory, setNewCategory] = useState("");
    const [refreshToken, setRefreshToken] = useState(0);
    const [teamCodeAttempts, setTeamCodeAttempts] = useState(0);

    const hasContext = Boolean(orgId && (userId || user?.id));

    useEffect(() => {
        const stored = window.localStorage.getItem("moneyops-custom-expense-categories");
        if (stored) {
            try {
                setCustomCategories(JSON.parse(stored));
            } catch {
                setCustomCategories([]);
            }
        }
    }, []);

    useEffect(() => {
        window.localStorage.setItem("moneyops-custom-expense-categories", JSON.stringify(customCategories));
    }, [customCategories]);

    useEffect(() => {
        if (!onboardingLoading && hasContext) {
            loadExpenseData(pageNumber);
        } else if (!onboardingLoading && !hasContext) {
            setLoading(false);
        }
    }, [onboardingLoading, hasContext, period, pageNumber, filters.category, filters.dateFrom, filters.dateTo, refreshToken]);

    useEffect(() => {
        const handleVoiceExpense = () => {
            setPageNumber(0);
            setRefreshToken((value) => value + 1);
        };

        window.addEventListener("voice:expense-created", handleVoiceExpense);
        window.addEventListener("expenses:updated", handleVoiceExpense);
        const interval = window.setInterval(handleVoiceExpense, 30000);

        return () => {
            window.removeEventListener("voice:expense-created", handleVoiceExpense);
            window.removeEventListener("expenses:updated", handleVoiceExpense);
            window.clearInterval(interval);
        };
    }, []);

    const buildHeaders = useCallback(async (extra = {}) => {
        const token = await getToken();
        return {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(userId || user?.id ? { "X-User-Id": userId || user?.id } : {}),
            ...(orgId ? { "X-Org-Id": orgId } : {}),
            ...extra,
        };
    }, [getToken, orgId, user?.id, userId]);

    async function loadExpenseData(page = 0) {
        if (!orgId) {
            setError("Organization context is missing.");
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            setError("");
            const headers = await buildHeaders();
            const expenseQuery = new URLSearchParams({
                orgId,
                page: String(page),
                size: "20",
            });

            if (filters.category !== "ALL") {
                expenseQuery.set("category", filters.category);
            }
            if (filters.dateFrom) {
                expenseQuery.set("dateFrom", filters.dateFrom);
            }
            if (filters.dateTo) {
                expenseQuery.set("dateTo", filters.dateTo);
            }

            const [summaryResponse, expenseResponse, categoryResponse] = await Promise.all([
                fetch(`/api/expenses/summary?orgId=${encodeURIComponent(orgId)}&period=${encodeURIComponent(period)}`, { headers }),
                fetch(`/api/expenses?${expenseQuery.toString()}`, { headers }),
                fetch("/api/expenses/categories", { headers }),
            ]);

            if (!summaryResponse.ok) {
                throw new Error("Failed to load expense summary");
            }
            if (!expenseResponse.ok) {
                throw new Error("Failed to load expense list");
            }

            const summaryPayload = parseApiPayload(await summaryResponse.json());
            const expensePayload = parseApiPayload(await expenseResponse.json());
            const categoryPayload = categoryResponse.ok ? parseApiPayload(await categoryResponse.json()) : DEFAULT_CATEGORIES;
            const mergedCategories = [...new Set([...(Array.isArray(categoryPayload) ? categoryPayload : DEFAULT_CATEGORIES), ...customCategories])];

            setSummary(summaryPayload || null);
            setExpensePage({
                content: expensePayload?.content || [],
                pageNumber: expensePayload?.pageNumber || 0,
                totalPages: expensePayload?.totalPages || 0,
                totalElements: expensePayload?.totalElements || 0,
                first: expensePayload?.first ?? true,
                last: expensePayload?.last ?? true,
            });
            setCategories(mergedCategories);
        } catch (requestError) {
            console.error("Failed to load expenses", requestError);
            setSummary(null);
            setExpensePage({
                content: [],
                pageNumber: 0,
                totalPages: 0,
                totalElements: 0,
                first: true,
                last: true,
            });
            setError(requestError.message || "Failed to load expenses");
        } finally {
            setLoading(false);
        }
    }

    async function handleSubmitExpense(event) {
        event.preventDefault();

        try {
            setSaving(true);
            const isEdit = Boolean(expenseForm.id);
            if (!isEdit && !expenseForm.teamActionCode?.trim()) {
                toast.error("Team security code is required");
                return;
            }

            const headers = await buildHeaders({ "Content-Type": "application/json" });
            const payload = {
                amount: Number(expenseForm.amount),
                category: expenseForm.category,
                description: expenseForm.description,
                date: expenseForm.date,
                paymentMethod: expenseForm.paymentMethod,
                receiptUrl: expenseForm.receiptUrl,
                teamActionCode: expenseForm.teamActionCode,
            };

            const response = await fetch(isEdit ? `/api/expenses/${expenseForm.id}` : "/api/expenses", {
                method: isEdit ? "PUT" : "POST",
                headers,
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const errorPayload = await response.json().catch(() => null);
                throw new Error(
                    errorPayload?.message ||
                    errorPayload?.error ||
                    (isEdit ? "Failed to update expense" : "Failed to record expense")
                );
            }

            toast.success(isEdit ? "Expense updated" : "Expense recorded");
            setTeamCodeAttempts(0);
            setExpenseForm(EMPTY_FORM);
            setIsExpenseModalOpen(false);
            setPageNumber(0);
            window.dispatchEvent(new CustomEvent("expenses:updated"));
            setRefreshToken((value) => value + 1);
        } catch (requestError) {
            const attempt = getTeamSecurityAttemptState(requestError, teamCodeAttempts);
            if (attempt.isSecurityCodeError) {
                toast.error(attempt.message);
                setExpenseForm((current) => ({ ...current, teamActionCode: "" }));
                if (attempt.shouldCancel) {
                    setIsExpenseModalOpen(false);
                    setExpenseForm(EMPTY_FORM);
                    setTeamCodeAttempts(0);
                } else {
                    setTeamCodeAttempts(attempt.nextAttempts);
                }
                return;
            }
            toast.error(requestError.message || "Could not save expense");
        } finally {
            setSaving(false);
        }
    }

    async function handleDeleteExpense(expenseId) {
        if (!window.confirm("Delete this expense?")) {
            return;
        }

        try {
            const headers = await buildHeaders();
            const response = await fetch(`/api/expenses/${expenseId}`, {
                method: "DELETE",
                headers,
            });
            if (!response.ok) {
                throw new Error("Failed to delete expense");
            }

            toast.success("Expense deleted");
            window.dispatchEvent(new CustomEvent("expenses:updated"));
            setRefreshToken((value) => value + 1);
        } catch (requestError) {
            toast.error(requestError.message || "Could not delete expense");
        }
    }

    function openCreateModal() {
        setExpenseForm({ ...EMPTY_FORM, category: categories[0] || "Other" });
        setTeamCodeAttempts(0);
        setIsExpenseModalOpen(true);
    }

    function openEditModal(expense) {
        setExpenseForm({
            id: expense.id,
            amount: expense.amount,
            category: expense.category || "Other",
            description: expense.description || "",
            date: expense.date || new Date().toISOString().slice(0, 10),
            paymentMethod: expense.paymentMethod || "",
            receiptUrl: expense.receiptUrl || "",
            teamActionCode: "",
        });
        setTeamCodeAttempts(0);
        setIsExpenseModalOpen(true);
    }

    function addCustomCategory() {
        const trimmed = newCategory.trim();
        if (!trimmed) {
            return;
        }
        if ([...DEFAULT_CATEGORIES, ...customCategories].some((category) => category.toLowerCase() === trimmed.toLowerCase())) {
            toast.error("Category already exists");
            return;
        }
        const updated = [...customCategories, trimmed].sort();
        setCustomCategories(updated);
        setCategories([...new Set([...DEFAULT_CATEGORIES, ...updated])]);
        setNewCategory("");
    }

    function removeCustomCategory(categoryName) {
        const updated = customCategories.filter((category) => category !== categoryName);
        setCustomCategories(updated);
        setCategories([...new Set([...DEFAULT_CATEGORIES, ...updated])]);
    }

    const filteredRows = useMemo(() => {
        return (expensePage.content || []).filter((expense) => {
            const amount = Number(expense.amount || 0);
            const amountMin = filters.amountMin ? Number(filters.amountMin) : null;
            const amountMax = filters.amountMax ? Number(filters.amountMax) : null;
            const minValid = amountMin === null || amount >= amountMin;
            const maxValid = amountMax === null || amount <= amountMax;
            return minValid && maxValid;
        });
    }, [expensePage.content, filters.amountMin, filters.amountMax]);

    if (loading || onboardingLoading) {
        return (
            <div className="flex items-center justify-center py-24">
                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
            </div>
        );
    }

    if (!hasContext) {
        return (
            <div className="mo-card rounded-2xl border border-dashed border-[#2A2A2A] bg-[#111111] px-6 py-10 text-center">
                <AlertCircle className="mx-auto mb-4 h-10 w-10 text-[#2F2F2F]" />
                <div className="text-lg font-semibold text-white">Workspace context is not ready</div>
                <div className="mt-2 text-sm text-[#A0A0A0]">
                    Expenses will load once your organization context is available.
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="mo-h1">Expense Tracker</h1>
                    <p className="mo-text-secondary mt-1">
                        Record, review, and analyze business expenses from manual entries and voice actions.
                    </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                    <button onClick={() => setIsCategoryModalOpen(true)} className="mo-btn-secondary flex items-center gap-2">
                        <Tag className="h-4 w-4" />
                        Categories
                    </button>
                    <button onClick={() => loadExpenseData(pageNumber)} className="mo-btn-secondary flex items-center gap-2">
                        <RefreshCw className="h-4 w-4" />
                        Refresh
                    </button>
                    <button onClick={openCreateModal} className="mo-btn-primary flex items-center gap-2">
                        <Plus className="h-4 w-4" />
                        Add Expense
                    </button>
                </div>
            </div>

            {error ? (
                <div className="rounded-2xl border border-[#F8717140] bg-[#111111] px-4 py-3 text-sm text-[#F87171]">
                    {error}
                </div>
            ) : null}

            <div className="grid gap-4 md:grid-cols-4">
                <div className="mo-stat-card">
                    <div className="mb-2 flex items-center justify-between">
                        <div className="text-sm text-[#A0A0A0]">Total This Period</div>
                        <Wallet className="h-4 w-4 text-[#4CBB17]" />
                    </div>
                    <div className="text-3xl font-bold text-white">{formatMoney(summary?.totalExpenses || 0)}</div>
                </div>
                <div className="mo-stat-card">
                    <div className="text-sm text-[#A0A0A0]">Average Monthly</div>
                    <div className="mt-2 text-3xl font-bold text-white">{formatMoney(summary?.avgMonthly || 0)}</div>
                </div>
                <div className="mo-stat-card">
                    <div className="text-sm text-[#A0A0A0]">Top Expense</div>
                    <div className="mt-2 text-lg font-semibold text-white">
                        {summary?.topExpense?.description || "No expense yet"}
                    </div>
                    <div className="mt-2 text-sm text-[#A0A0A0]">
                        {summary?.topExpense?.amount ? formatMoney(summary.topExpense.amount) : "--"}
                    </div>
                </div>
                <div className="mo-stat-card">
                    <div className="text-sm text-[#A0A0A0]">Period</div>
                    <select
                        value={period}
                        onChange={(event) => {
                            setPageNumber(0);
                            setPeriod(event.target.value);
                        }}
                        className="mt-3 w-full rounded-lg border border-[#2A2A2A] bg-[#0E0E0E] px-3 py-2 text-sm text-white outline-none"
                    >
                        <option value="monthly">This Month</option>
                        <option value="quarterly">This Quarter</option>
                        <option value="yearly">This Year</option>
                    </select>
                </div>
            </div>

            <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
                <div className="mo-card">
                    <h2 className="mo-h2">By Category</h2>
                    <p className="mo-text-secondary mt-1">Distribution of recorded expenses by category.</p>
                    <div className="mt-4 h-[320px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={summary?.byCategory || []}
                                    dataKey="total"
                                    nameKey="category"
                                    innerRadius={70}
                                    outerRadius={110}
                                    paddingAngle={3}
                                >
                                    {(summary?.byCategory || []).map((entry, index) => (
                                        <Cell key={`${entry.category}-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip formatter={(value) => formatMoney(value)} />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="mo-card">
                    <h2 className="mo-h2">Trend</h2>
                    <p className="mo-text-secondary mt-1">Expense movement across recent periods.</p>
                    <div className="mt-4 h-[320px]">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={summary?.trend || []}>
                                <XAxis dataKey="month" stroke="#A0A0A0" />
                                <YAxis stroke="#A0A0A0" tickFormatter={(value) => `${Math.round(Number(value) / 1000)}k`} />
                                <Tooltip formatter={(value) => formatMoney(value)} />
                                <Line type="monotone" dataKey="total" stroke="#4CBB17" strokeWidth={3} dot={{ r: 4 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            <ExpenseInsightsPanel
                orgId={orgId}
                buildHeaders={buildHeaders}
                expenseSummary={summary}
                period={period}
                refreshToken={refreshToken}
            />

            <div className="mo-card">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <div>
                        <h2 className="mo-h2">Expense Table</h2>
                        <p className="mo-text-secondary mt-1">Filter and manage recorded expenses.</p>
                    </div>
                    <div className="text-sm text-[#A0A0A0]">
                        Showing {filteredRows.length} of {expensePage.totalElements} expenses
                    </div>
                </div>

                <div className="grid gap-3 rounded-2xl border border-[#202020] bg-[#111111] p-4 md:grid-cols-2 xl:grid-cols-5">
                    <select
                        value={filters.category}
                        onChange={(event) => {
                            setPageNumber(0);
                            setFilters((current) => ({ ...current, category: event.target.value }));
                        }}
                        className="rounded-lg border border-[#2A2A2A] bg-[#0E0E0E] px-3 py-2 text-sm text-white outline-none"
                    >
                        <option value="ALL">All Categories</option>
                        {categories.map((category) => (
                            <option key={category} value={category}>{category}</option>
                        ))}
                    </select>
                    <input
                        type="date"
                        value={filters.dateFrom}
                        onChange={(event) => {
                            setPageNumber(0);
                            setFilters((current) => ({ ...current, dateFrom: event.target.value }));
                        }}
                        className="rounded-lg border border-[#2A2A2A] bg-[#0E0E0E] px-3 py-2 text-sm text-white outline-none"
                    />
                    <input
                        type="date"
                        value={filters.dateTo}
                        onChange={(event) => {
                            setPageNumber(0);
                            setFilters((current) => ({ ...current, dateTo: event.target.value }));
                        }}
                        className="rounded-lg border border-[#2A2A2A] bg-[#0E0E0E] px-3 py-2 text-sm text-white outline-none"
                    />
                    <input
                        type="number"
                        placeholder="Min Amount"
                        value={filters.amountMin}
                        onChange={(event) => setFilters((current) => ({ ...current, amountMin: event.target.value }))}
                        className="rounded-lg border border-[#2A2A2A] bg-[#0E0E0E] px-3 py-2 text-sm text-white outline-none"
                    />
                    <input
                        type="number"
                        placeholder="Max Amount"
                        value={filters.amountMax}
                        onChange={(event) => setFilters((current) => ({ ...current, amountMax: event.target.value }))}
                        className="rounded-lg border border-[#2A2A2A] bg-[#0E0E0E] px-3 py-2 text-sm text-white outline-none"
                    />
                </div>

                <div className="mt-5 overflow-hidden rounded-2xl border border-[#222222]">
                    <table className="w-full text-sm">
                        <thead className="bg-[#141414]">
                            <tr>
                                {["Description", "Category", "Date", "Payment", "Receipt", "Amount", "Actions"].map((heading) => (
                                    <th key={heading} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[#8F8F8F]">
                                        {heading}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#1F1F1F] bg-[#0D0D0D]">
                            {filteredRows.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-4 py-10 text-center text-sm text-[#A0A0A0]">
                                        No expenses matched the current filters.
                                    </td>
                                </tr>
                            ) : (
                                filteredRows.map((expense) => (
                                    <tr key={expense.id} className="hover:bg-[#141414]">
                                        <td className="px-4 py-3 text-white">{expense.description || expense.category || "Expense"}</td>
                                        <td className="px-4 py-3 text-[#A0A0A0]">{expense.category || "Other"}</td>
                                        <td className="px-4 py-3 text-[#A0A0A0]">{expense.date || "--"}</td>
                                        <td className="px-4 py-3 text-[#A0A0A0]">{expense.paymentMethod || "--"}</td>
                                        <td className="px-4 py-3 text-[#60A5FA]">
                                            {expense.receiptUrl ? (
                                                <a href={expense.receiptUrl} target="_blank" rel="noreferrer" className="hover:text-[#93C5FD]">
                                                    Open
                                                </a>
                                            ) : "--"}
                                        </td>
                                        <td className="px-4 py-3 font-semibold text-[#F87171]">{formatMoney(expense.amount)}</td>
                                        <td className="px-4 py-3">
                                            <div className="flex items-center gap-2">
                                                <button onClick={() => openEditModal(expense)} className="rounded-lg border border-[#2A2A2A] p-2 text-[#A0A0A0] hover:text-white">
                                                    <Pencil className="h-4 w-4" />
                                                </button>
                                                <button onClick={() => handleDeleteExpense(expense.id)} className="rounded-lg border border-[#2A2A2A] p-2 text-[#A0A0A0] hover:text-[#F87171]">
                                                    <Trash2 className="h-4 w-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                <div className="mt-5 flex items-center justify-between gap-3">
                    <div className="text-sm text-[#A0A0A0]">
                        Page {expensePage.pageNumber + 1} of {Math.max(expensePage.totalPages, 1)}
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setPageNumber((current) => Math.max(current - 1, 0))}
                            disabled={expensePage.first}
                            className="mo-btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            Previous
                        </button>
                        <button
                            onClick={() => setPageNumber((current) => current + 1)}
                            disabled={expensePage.last}
                            className="mo-btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            Next
                        </button>
                    </div>
                </div>
            </div>

            {isExpenseModalOpen ? (
                <ModalShell title={expenseForm.id ? "Edit Expense" : "Add Expense"} onClose={() => setIsExpenseModalOpen(false)}>
                    <form onSubmit={handleSubmitExpense} className="grid gap-4 md:grid-cols-2">
                        <label className="grid gap-2 text-sm text-[#A0A0A0]">
                            Amount
                            <input
                                required
                                type="number"
                                min="0"
                                step="0.01"
                                value={expenseForm.amount}
                                onChange={(event) => setExpenseForm((current) => ({ ...current, amount: event.target.value }))}
                                className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-white outline-none"
                            />
                        </label>
                        <label className="grid gap-2 text-sm text-[#A0A0A0]">
                            Category
                            <select
                                value={expenseForm.category}
                                onChange={(event) => setExpenseForm((current) => ({ ...current, category: event.target.value }))}
                                className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-white outline-none"
                            >
                                {categories.map((category) => (
                                    <option key={category} value={category}>{category}</option>
                                ))}
                            </select>
                        </label>
                        <label className="grid gap-2 text-sm text-[#A0A0A0] md:col-span-2">
                            Description
                            <input
                                required
                                value={expenseForm.description}
                                onChange={(event) => setExpenseForm((current) => ({ ...current, description: event.target.value }))}
                                className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-white outline-none"
                            />
                        </label>
                        <label className="grid gap-2 text-sm text-[#A0A0A0]">
                            Date
                            <input
                                required
                                type="date"
                                value={expenseForm.date}
                                onChange={(event) => setExpenseForm((current) => ({ ...current, date: event.target.value }))}
                                className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-white outline-none"
                            />
                        </label>
                        <label className="grid gap-2 text-sm text-[#A0A0A0]">
                            Payment Method
                            <input
                                value={expenseForm.paymentMethod}
                                onChange={(event) => setExpenseForm((current) => ({ ...current, paymentMethod: event.target.value }))}
                                className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-white outline-none"
                            />
                        </label>
                        <label className="grid gap-2 text-sm text-[#A0A0A0] md:col-span-2">
                            Receipt URL
                            <input
                                type="url"
                                value={expenseForm.receiptUrl}
                                onChange={(event) => setExpenseForm((current) => ({ ...current, receiptUrl: event.target.value }))}
                                className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-white outline-none"
                            />
                        </label>
                        {!expenseForm.id ? (
                            <label className="grid gap-2 text-sm text-[#A0A0A0] md:col-span-2">
                                Team Security Code
                                <input
                                    required
                                    type="password"
                                    autoComplete="new-password"
                                    data-lpignore="true"
                                    data-1p-ignore="true"
                                    value={expenseForm.teamActionCode}
                                    onChange={(event) => setExpenseForm((current) => ({ ...current, teamActionCode: event.target.value }))}
                                    className="rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-white outline-none"
                                    placeholder="Enter team security code"
                                />
                            </label>
                        ) : null}
                        <div className="md:col-span-2 flex justify-end">
                            <button disabled={saving} type="submit" className="mo-btn-primary min-w-32">
                                {saving ? "Saving..." : expenseForm.id ? "Update Expense" : "Save Expense"}
                            </button>
                        </div>
                    </form>
                </ModalShell>
            ) : null}

            {isCategoryModalOpen ? (
                <ModalShell title="Manage Categories" onClose={() => setIsCategoryModalOpen(false)}>
                    <div className="space-y-4">
                        <div className="flex gap-2">
                            <input
                                value={newCategory}
                                onChange={(event) => setNewCategory(event.target.value)}
                                placeholder="Add a custom category"
                                className="flex-1 rounded-lg border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-white outline-none"
                            />
                            <button onClick={addCustomCategory} className="mo-btn-primary">Add</button>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {categories.map((category) => {
                                const isCustom = customCategories.includes(category);
                                return (
                                    <div key={category} className="inline-flex items-center gap-2 rounded-full border border-[#2A2A2A] bg-[#111111] px-3 py-1.5 text-sm text-white">
                                        <span>{category}</span>
                                        {isCustom ? (
                                            <button onClick={() => removeCustomCategory(category)} className="text-[#F87171] hover:text-[#FCA5A5]">
                                                <Trash2 className="h-3.5 w-3.5" />
                                            </button>
                                        ) : null}
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </ModalShell>
            ) : null}
        </div>
    );
}
