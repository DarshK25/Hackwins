import { useEffect, useState } from "react";
import {
    AlertTriangle,
    BarChart3,
    Calendar,
    Loader2,
    Pencil,
    Plus,
    RefreshCw,
    Target,
    Wallet,
} from "lucide-react";
import {
    Bar,
    BarChart,
    CartesianGrid,
    Legend,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { useAuth, useUser } from "@clerk/clerk-react";
import { toast } from "sonner";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";

const STATUS_STYLES = {
    ON_TRACK: {
        bar: "#4CBB17",
        bg: "bg-[#4CBB1715]",
        border: "border-[#4CBB1740]",
        text: "text-[#4CBB17]",
    },
    WARNING: {
        bar: "#FFB300",
        bg: "bg-[#FFB30015]",
        border: "border-[#FFB30040]",
        text: "text-[#FFB300]",
    },
    EXCEEDED: {
        bar: "#CD1C18",
        bg: "bg-[#CD1C1815]",
        border: "border-[#CD1C1840]",
        text: "text-[#CD1C18]",
    },
};

const PERIOD_OPTIONS = [
    { value: "MONTHLY", label: "Monthly" },
    { value: "QUARTERLY", label: "Quarterly" },
    { value: "YEARLY", label: "Yearly" },
    { value: "CUSTOM", label: "Custom" },
];

const inputClassName = "w-full rounded-lg border border-[#2A2A2A] bg-[#121212] px-3 py-2.5 text-sm text-white outline-none transition focus:border-[#4CBB17]";

function startOfCurrentMonth() {
    const date = new Date();
    const year = date.getFullYear();
    const month = `${date.getMonth() + 1}`.padStart(2, "0");
    return `${year}-${month}-01`;
}

function deriveEndDate(period, startDate, currentEndDate) {
    if (!startDate) {
        return "";
    }

    if (period === "CUSTOM") {
        return currentEndDate || startDate;
    }

    const date = new Date(`${startDate}T00:00:00`);
    if (Number.isNaN(date.getTime())) {
        return currentEndDate || "";
    }

    if (period === "MONTHLY") {
        date.setMonth(date.getMonth() + 1, 0);
        return date.toISOString().slice(0, 10);
    }

    if (period === "QUARTERLY") {
        const end = new Date(`${startDate}T00:00:00`);
        end.setMonth(end.getMonth() + 3);
        end.setDate(end.getDate() - 1);
        return end.toISOString().slice(0, 10);
    }

    if (period === "YEARLY") {
        const end = new Date(`${startDate}T00:00:00`);
        end.setFullYear(end.getFullYear() + 1);
        end.setDate(end.getDate() - 1);
        return end.toISOString().slice(0, 10);
    }

    return currentEndDate || startDate;
}

function emptyFormState() {
    const startDate = startOfCurrentMonth();
    return {
        name: "",
        period: "MONTHLY",
        startDate,
        endDate: deriveEndDate("MONTHLY", startDate, ""),
        categories: [{ name: "", limit: "" }],
    };
}

function formFromBudget(budget) {
    const startDate = budget?.startDate || startOfCurrentMonth();
    const period = budget?.period || "MONTHLY";
    return {
        name: budget?.name || "",
        period,
        startDate,
        endDate: budget?.endDate || deriveEndDate(period, startDate, ""),
        categories: (budget?.categories || []).map((category) => ({
            name: category.name || "",
            limit: category.limit != null ? String(category.limit) : "",
        })),
    };
}

function formatMoney(value) {
    const amount = Number(value || 0);
    return `₹${amount.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

function formatPercent(value) {
    return `${Number(value || 0).toFixed(1)}%`;
}

function formatDate(value) {
    if (!value) {
        return "N/A";
    }
    const date = new Date(`${value}T00:00:00`);
    return date.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
    });
}

function formatRange(startDate, endDate) {
    return `${formatDate(startDate)} - ${formatDate(endDate)}`;
}

function progressPercent(actual, budgeted) {
    const normalizedBudget = Number(budgeted || 0);
    const normalizedActual = Number(actual || 0);
    if (normalizedBudget <= 0) {
        return normalizedActual > 0 ? 100 : 0;
    }
    return Math.min((normalizedActual / normalizedBudget) * 100, 100);
}

function extractErrorMessage(payload, fallbackMessage) {
    if (!payload) {
        return fallbackMessage;
    }
    if (typeof payload === "string") {
        return payload;
    }
    return payload.message || payload.error || payload.data?.message || fallbackMessage;
}

async function parseError(response, fallbackMessage) {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
        const payload = await response.json().catch(() => null);
        return extractErrorMessage(payload, fallbackMessage);
    }
    const text = await response.text().catch(() => "");
    return text || fallbackMessage;
}

function SummaryCard({ label, value, subValue, icon: Icon, accent }) {
    return (
        <div className="mo-stat-card">
            <div className="mb-3 flex items-center justify-between">
                <span className="text-sm font-medium text-[#A0A0A0]">{label}</span>
                <Icon className="h-4 w-4" style={{ color: accent || "#A0A0A0" }} />
            </div>
            <div className="text-2xl font-bold text-white">{value}</div>
            {subValue ? (
                <div className="mt-1 text-xs text-[#A0A0A0]">{subValue}</div>
            ) : null}
        </div>
    );
}

function ChartTooltip({ active, payload, label }) {
    if (!active || !payload?.length) {
        return null;
    }

    return (
        <div className="rounded-xl border border-[#2A2A2A] bg-[#121212] px-3 py-2 text-sm shadow-lg">
            <div className="mb-1 text-xs text-[#A0A0A0]">{label}</div>
            {payload.map((entry) => (
                <div key={entry.dataKey} className="flex items-center justify-between gap-4">
                    <span style={{ color: entry.color }}>{entry.name}</span>
                    <span className="text-white">{formatMoney(entry.value)}</span>
                </div>
            ))}
        </div>
    );
}

export default function BudgetAnalysis() {
    const { getToken } = useAuth();
    const { user } = useUser();
    const { orgId, loading: onboardingLoading } = useOnboardingStatus();

    const [budgets, setBudgets] = useState([]);
    const [selectedBudgetId, setSelectedBudgetId] = useState(null);
    const [selectedBudget, setSelectedBudget] = useState(null);
    const [analysis, setAnalysis] = useState(null);
    const [loadingList, setLoadingList] = useState(true);
    const [loadingDetail, setLoadingDetail] = useState(false);
    const [saving, setSaving] = useState(false);
    const [deletingBudgetId, setDeletingBudgetId] = useState(null);
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [editingBudgetId, setEditingBudgetId] = useState(null);
    const [form, setForm] = useState(emptyFormState());

    useEffect(() => {
        if (!user?.id || !orgId) {
            return;
        }
        fetchBudgets();
    }, [user?.id, orgId]);

    useEffect(() => {
        if (!selectedBudgetId || !user?.id || !orgId) {
            return;
        }
        fetchBudgetDetail(selectedBudgetId);
    }, [selectedBudgetId, user?.id, orgId]);

    async function buildHeaders(includeJson = false) {
        const token = await getToken();
        return {
            ...(includeJson ? { "Content-Type": "application/json" } : {}),
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            "X-User-Id": user?.id,
            "X-Org-Id": orgId,
        };
    }

    async function fetchBudgets(preferredBudgetId) {
        if (!orgId) {
            return;
        }

        try {
            setLoadingList(true);
            const headers = await buildHeaders();
            const response = await fetch(`/api/budgets?orgId=${encodeURIComponent(orgId)}`, { headers });

            if (!response.ok) {
                throw new Error(await parseError(response, "Failed to load budgets"));
            }

            const data = await response.json();
            const budgetList = Array.isArray(data) ? data : [];
            setBudgets(budgetList);

            const nextBudgetId =
                preferredBudgetId ||
                (budgetList.some((budget) => budget.id === selectedBudgetId) ? selectedBudgetId : null) ||
                budgetList[0]?.id ||
                null;

            setSelectedBudgetId(nextBudgetId);
            if (!nextBudgetId) {
                setSelectedBudget(null);
                setAnalysis(null);
            } else if (nextBudgetId === selectedBudgetId) {
                await fetchBudgetDetail(nextBudgetId);
            }
        } catch (error) {
            console.error("Failed to load budgets", error);
            toast.error(error.message || "Failed to load budgets");
            setBudgets([]);
            setSelectedBudgetId(null);
            setSelectedBudget(null);
            setAnalysis(null);
        } finally {
            setLoadingList(false);
        }
    }

    async function fetchBudgetDetail(budgetId) {
        try {
            setLoadingDetail(true);
            const headers = await buildHeaders();
            const [budgetResponse, analysisResponse] = await Promise.all([
                fetch(`/api/budgets/${budgetId}?orgId=${encodeURIComponent(orgId)}`, { headers }),
                fetch(`/api/budgets/${budgetId}/analysis?orgId=${encodeURIComponent(orgId)}`, { headers }),
            ]);

            if (!budgetResponse.ok) {
                throw new Error(await parseError(budgetResponse, "Failed to load budget"));
            }
            if (!analysisResponse.ok) {
                throw new Error(await parseError(analysisResponse, "Failed to load budget analysis"));
            }

            const budgetData = await budgetResponse.json();
            const analysisData = await analysisResponse.json();
            setSelectedBudget(budgetData);
            setAnalysis(analysisData);
        } catch (error) {
            console.error("Failed to load budget detail", error);
            toast.error(error.message || "Failed to load budget detail");
            setSelectedBudget(null);
            setAnalysis(null);
        } finally {
            setLoadingDetail(false);
        }
    }

    function openCreateDialog() {
        setEditingBudgetId(null);
        setForm(emptyFormState());
        setIsDialogOpen(true);
    }

    function openEditDialog() {
        if (!selectedBudget) {
            return;
        }
        setEditingBudgetId(selectedBudget.id);
        setForm(formFromBudget(selectedBudget));
        setIsDialogOpen(true);
    }

    function updateFormField(field, value) {
        setForm((current) => {
            const next = { ...current, [field]: value };
            if (field === "period" || field === "startDate") {
                next.endDate = deriveEndDate(
                    field === "period" ? value : next.period,
                    field === "startDate" ? value : next.startDate,
                    next.endDate
                );
            }
            return next;
        });
    }

    function updateCategory(index, field, value) {
        setForm((current) => ({
            ...current,
            categories: current.categories.map((category, categoryIndex) =>
                categoryIndex === index ? { ...category, [field]: value } : category
            ),
        }));
    }

    function addCategoryRow() {
        setForm((current) => ({
            ...current,
            categories: [...current.categories, { name: "", limit: "" }],
        }));
    }

    function removeCategoryRow(index) {
        setForm((current) => ({
            ...current,
            categories:
                current.categories.length === 1
                    ? current.categories
                    : current.categories.filter((_, categoryIndex) => categoryIndex !== index),
        }));
    }

    async function handleSaveBudget() {
        const trimmedCategories = form.categories
            .map((category) => ({
                name: category.name.trim(),
                limit: category.limit,
            }))
            .filter((category) => category.name || category.limit);

        if (!form.name.trim()) {
            toast.error("Budget name is required");
            return;
        }
        if (trimmedCategories.length === 0) {
            toast.error("Add at least one category");
            return;
        }
        if (trimmedCategories.some((category) => !category.name || category.limit === "")) {
            toast.error("Each category needs a name and limit");
            return;
        }

        const payload = {
            orgId,
            name: form.name.trim(),
            period: form.period,
            startDate: form.startDate,
            endDate: form.period === "CUSTOM" ? form.endDate : deriveEndDate(form.period, form.startDate, form.endDate),
            categories: trimmedCategories.map((category) => ({
                name: category.name,
                limit: Number(category.limit),
            })),
        };

        try {
            setSaving(true);
            const headers = await buildHeaders(true);
            const endpoint = editingBudgetId ? `/api/budgets/${editingBudgetId}?orgId=${encodeURIComponent(orgId)}` : "/api/budgets";
            const response = await fetch(endpoint, {
                method: editingBudgetId ? "PUT" : "POST",
                headers,
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                throw new Error(await parseError(response, editingBudgetId ? "Failed to update budget" : "Failed to create budget"));
            }

            const savedBudget = await response.json();
            toast.success(editingBudgetId ? "Budget updated" : "Budget created");
            setIsDialogOpen(false);
            await fetchBudgets(savedBudget.id);
            await fetchBudgetDetail(savedBudget.id);
        } catch (error) {
            console.error("Failed to save budget", error);
            toast.error(error.message || "Failed to save budget");
        } finally {
            setSaving(false);
        }
    }

    async function handleDeleteBudget(budgetId) {
        if (!window.confirm("Delete this budget? This performs a soft delete and hides it from the Finance page.")) {
            return;
        }

        try {
            setDeletingBudgetId(budgetId);
            const headers = await buildHeaders();
            const response = await fetch(`/api/budgets/${budgetId}?orgId=${encodeURIComponent(orgId)}`, {
                method: "DELETE",
                headers,
            });

            if (!response.ok) {
                throw new Error(await parseError(response, "Failed to delete budget"));
            }

            const remainingBudgets = budgets.filter((budget) => budget.id !== budgetId);
            const nextBudgetId = remainingBudgets[0]?.id || null;
            toast.success("Budget deleted");
            setSelectedBudgetId((current) => (current === budgetId ? nextBudgetId : current));
            await fetchBudgets(nextBudgetId);
        } catch (error) {
            console.error("Failed to delete budget", error);
            toast.error(error.message || "Failed to delete budget");
        } finally {
            setDeletingBudgetId(null);
        }
    }

    const chartData = (analysis?.categories || []).map((category) => ({
        name: category.name,
        Budgeted: Number(category.budgeted || 0),
        Actual: Number(category.actual || 0),
    }));

    return (
        <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 className="mo-h1">Finances</h1>
                    <p className="mo-text-secondary mt-1">
                        Plan spend by category, track actuals, and catch overages before they land.
                    </p>
                </div>
                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={() => fetchBudgets()}
                        className="mo-btn-secondary flex items-center gap-2"
                        disabled={loadingList}
                    >
                        {loadingList ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                        Refresh
                    </button>
                    <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
                        <DialogTrigger asChild>
                            <button onClick={openCreateDialog} className="mo-btn-primary flex items-center gap-2">
                                <Plus className="h-4 w-4" />
                                New Budget
                            </button>
                        </DialogTrigger>
                        <DialogContent className="max-h-[90vh] overflow-y-auto border-[#2A2A2A] bg-[#0F0F10] text-white sm:max-w-3xl">
                            <DialogHeader>
                                <DialogTitle>{editingBudgetId ? "Edit Budget" : "Create Budget"}</DialogTitle>
                            </DialogHeader>
                            <div className="grid gap-5 py-2">
                                <div className="grid gap-4 md:grid-cols-2">
                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium text-[#A0A0A0]">Budget name</label>
                                        <input
                                            className={inputClassName}
                                            placeholder="FY26 Growth Budget"
                                            value={form.name}
                                            onChange={(event) => updateFormField("name", event.target.value)}
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium text-[#A0A0A0]">Period</label>
                                        <select
                                            className={inputClassName}
                                            value={form.period}
                                            onChange={(event) => updateFormField("period", event.target.value)}
                                        >
                                            {PERIOD_OPTIONS.map((option) => (
                                                <option key={option.value} value={option.value} className="bg-[#121212]">
                                                    {option.label}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                </div>

                                <div className="grid gap-4 md:grid-cols-2">
                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium text-[#A0A0A0]">Start date</label>
                                        <input
                                            className={inputClassName}
                                            type="date"
                                            value={form.startDate}
                                            onChange={(event) => updateFormField("startDate", event.target.value)}
                                        />
                                    </div>
                                    <div className="grid gap-2">
                                        <label className="text-sm font-medium text-[#A0A0A0]">
                                            {form.period === "CUSTOM" ? "End date" : "End date (auto)"}
                                        </label>
                                        <input
                                            className={inputClassName}
                                            type="date"
                                            value={form.period === "CUSTOM" ? form.endDate : deriveEndDate(form.period, form.startDate, form.endDate)}
                                            onChange={(event) => updateFormField("endDate", event.target.value)}
                                            disabled={form.period !== "CUSTOM"}
                                        />
                                    </div>
                                </div>

                                <div className="rounded-2xl border border-[#2A2A2A] bg-[#111111] p-4">
                                    <div className="mb-4 flex items-center justify-between">
                                        <div>
                                            <h3 className="text-sm font-semibold text-white">Categories</h3>
                                            <p className="text-xs text-[#A0A0A0]">Set the spend limit for each tracked category.</p>
                                        </div>
                                        <button onClick={addCategoryRow} className="mo-btn-secondary text-xs">
                                            Add Category
                                        </button>
                                    </div>
                                    <div className="space-y-3">
                                        {form.categories.map((category, index) => (
                                            <div key={`${index}-${category.name}`} className="grid gap-3 md:grid-cols-[1.2fr_0.8fr_auto]">
                                                <input
                                                    className={inputClassName}
                                                    placeholder="Marketing"
                                                    value={category.name}
                                                    onChange={(event) => updateCategory(index, "name", event.target.value)}
                                                />
                                                <input
                                                    className={inputClassName}
                                                    type="number"
                                                    min="0"
                                                    placeholder="50000"
                                                    value={category.limit}
                                                    onChange={(event) => updateCategory(index, "limit", event.target.value)}
                                                />
                                                <button
                                                    onClick={() => removeCategoryRow(index)}
                                                    className="rounded-lg border border-[#2A2A2A] px-3 py-2 text-sm text-[#A0A0A0] transition hover:border-[#CD1C18] hover:text-[#CD1C18]"
                                                    disabled={form.categories.length === 1}
                                                >
                                                    Remove
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                <div className="flex justify-end gap-2">
                                    <button className="mo-btn-secondary" onClick={() => setIsDialogOpen(false)} disabled={saving}>
                                        Cancel
                                    </button>
                                    <button className="mo-btn-primary flex items-center gap-2" onClick={handleSaveBudget} disabled={saving}>
                                        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wallet className="h-4 w-4" />}
                                        {editingBudgetId ? "Save Changes" : "Create Budget"}
                                    </button>
                                </div>
                            </div>
                        </DialogContent>
                    </Dialog>
                </div>
            </div>

            {!onboardingLoading && !orgId ? (
                <div className="mo-card flex flex-col items-center justify-center py-16 text-center">
                    <AlertTriangle className="mb-4 h-12 w-12 text-[#FFB300]" />
                    <h2 className="text-xl font-semibold text-white">Organization context is missing</h2>
                    <p className="mt-2 max-w-lg text-sm text-[#A0A0A0]">
                        Finish onboarding or refresh your workspace so MoneyOps can load the right budget data.
                    </p>
                </div>
            ) : null}

            {orgId ? (
                <div className="grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
                    <div className="mo-card h-fit">
                        <div className="mb-4 flex items-center justify-between">
                            <div>
                                <h2 className="mo-h2">Budgets</h2>
                                <p className="mt-1 text-sm text-[#A0A0A0]">Pick a budget to inspect category-level spend.</p>
                            </div>
                            <div className="rounded-xl border border-[#2A2A2A] bg-[#111111] px-3 py-2 text-sm text-white">
                                {budgets.length}
                            </div>
                        </div>

                        {loadingList ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="h-6 w-6 animate-spin text-[#4CBB17]" />
                            </div>
                        ) : budgets.length === 0 ? (
                            <div className="rounded-2xl border border-dashed border-[#2A2A2A] bg-[#111111] px-4 py-10 text-center">
                                <Wallet className="mx-auto mb-3 h-10 w-10 text-[#2F2F2F]" />
                                <h3 className="text-base font-semibold text-white">No budgets yet</h3>
                                <p className="mt-2 text-sm text-[#A0A0A0]">
                                    Create your first budget to compare planned limits against actual expenses.
                                </p>
                                <button onClick={openCreateDialog} className="mo-btn-primary mt-5">
                                    Create Budget
                                </button>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {budgets.map((budget) => {
                                    const isSelected = selectedBudgetId === budget.id;
                                    return (
                                        <button
                                            key={budget.id}
                                            onClick={() => setSelectedBudgetId(budget.id)}
                                            className={`w-full rounded-2xl border p-4 text-left transition ${
                                                isSelected
                                                    ? "border-[#4CBB17] bg-[#4CBB1710]"
                                                    : "border-[#2A2A2A] bg-[#111111] hover:border-[#3D3D3D]"
                                            }`}
                                        >
                                            <div className="flex items-start justify-between gap-3">
                                                <div>
                                                    <div className="font-semibold text-white">{budget.name}</div>
                                                    <div className="mt-1 text-xs uppercase tracking-wide text-[#A0A0A0]">
                                                        {budget.period}
                                                    </div>
                                                </div>
                                                <div className={`rounded-full px-2 py-1 text-xs font-medium ${isSelected ? "bg-[#4CBB171A] text-[#4CBB17]" : "bg-[#1B1B1B] text-[#A0A0A0]"}`}>
                                                    {formatPercent(budget.utilizationPercent)}
                                                </div>
                                            </div>
                                            <div className="mt-3 text-sm text-[#A0A0A0]">{formatRange(budget.startDate, budget.endDate)}</div>
                                            <div className="mt-4 flex items-center justify-between text-sm">
                                                <span className="text-[#A0A0A0]">Budget</span>
                                                <span className="font-medium text-white">{formatMoney(budget.totalBudget)}</span>
                                            </div>
                                            <div className="mt-1 flex items-center justify-between text-sm">
                                                <span className="text-[#A0A0A0]">Spent</span>
                                                <span className="font-medium text-white">{formatMoney(budget.totalSpent)}</span>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    <div className="flex flex-col gap-6">
                        {loadingDetail ? (
                            <div className="mo-card flex items-center justify-center py-24">
                                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
                            </div>
                        ) : !selectedBudget || !analysis ? (
                            <div className="mo-card flex flex-col items-center justify-center py-24 text-center">
                                <BarChart3 className="mb-4 h-12 w-12 text-[#2F2F2F]" />
                                <h2 className="text-xl font-semibold text-white">Choose a budget</h2>
                                <p className="mt-2 max-w-lg text-sm text-[#A0A0A0]">
                                    Select a budget from the left to review actual spending, category status, and matching transactions.
                                </p>
                            </div>
                        ) : (
                            <>
                                <div className="mo-card">
                                    <div className="flex flex-wrap items-start justify-between gap-4">
                                        <div>
                                            <div className="flex flex-wrap items-center gap-2">
                                                <h2 className="mo-h2">{selectedBudget.name}</h2>
                                                <span className="rounded-full border border-[#2A2A2A] bg-[#111111] px-3 py-1 text-xs font-medium text-[#A0A0A0]">
                                                    {selectedBudget.period}
                                                </span>
                                            </div>
                                            <p className="mt-2 flex items-center gap-2 text-sm text-[#A0A0A0]">
                                                <Calendar className="h-4 w-4" />
                                                {formatRange(selectedBudget.startDate, selectedBudget.endDate)}
                                            </p>
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            <button onClick={openEditDialog} className="mo-btn-secondary flex items-center gap-2">
                                                <Pencil className="h-4 w-4" />
                                                Edit
                                            </button>
                                            <button
                                                onClick={() => handleDeleteBudget(selectedBudget.id)}
                                                className="rounded-lg border border-[#CD1C1840] bg-[#CD1C1810] px-4 py-2 text-sm font-medium text-[#CD1C18] transition hover:bg-[#CD1C1818]"
                                                disabled={deletingBudgetId === selectedBudget.id}
                                            >
                                                {deletingBudgetId === selectedBudget.id ? "Deleting..." : "Delete"}
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                                    <SummaryCard
                                        label="Total Budget"
                                        value={formatMoney(analysis.totalBudget)}
                                        subValue={`${analysis.categories.length} tracked categories`}
                                        icon={Wallet}
                                        accent="#60A5FA"
                                    />
                                    <SummaryCard
                                        label="Total Spent"
                                        value={formatMoney(analysis.totalSpent)}
                                        subValue={`${formatPercent(analysis.utilizationPercent)} used`}
                                        icon={BarChart3}
                                        accent="#4CBB17"
                                    />
                                    <SummaryCard
                                        label="Remaining"
                                        value={formatMoney(analysis.remaining)}
                                        subValue={Number(analysis.remaining) < 0 ? "Overspent budget" : "Budget still available"}
                                        icon={Target}
                                        accent={Number(analysis.remaining) < 0 ? "#CD1C18" : "#ffffff"}
                                    />
                                    <SummaryCard
                                        label="At Risk"
                                        value={String(analysis.categories.filter((category) => category.status !== "ON_TRACK").length)}
                                        subValue="Warning or exceeded categories"
                                        icon={AlertTriangle}
                                        accent="#FFB300"
                                    />
                                </div>

                                <div className="grid gap-6 2xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
                                    <div className="mo-card">
                                        <div className="mb-4">
                                            <h3 className="mo-h2">Budgeted vs Actual</h3>
                                            <p className="mt-1 text-sm text-[#A0A0A0]">Compare planned limits against recorded expenses for each category.</p>
                                        </div>
                                        <div className="h-[360px]">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <BarChart data={chartData} barGap={8}>
                                                    <CartesianGrid stroke="#1F1F1F" vertical={false} />
                                                    <XAxis dataKey="name" stroke="#8F8F8F" tickLine={false} axisLine={false} />
                                                    <YAxis
                                                        stroke="#8F8F8F"
                                                        tickLine={false}
                                                        axisLine={false}
                                                        tickFormatter={(value) => `₹${Number(value).toLocaleString("en-IN")}`}
                                                    />
                                                    <Tooltip content={<ChartTooltip />} />
                                                    <Legend />
                                                    <Bar dataKey="Budgeted" fill="#60A5FA" radius={[6, 6, 0, 0]} />
                                                    <Bar dataKey="Actual" fill="#4CBB17" radius={[6, 6, 0, 0]} />
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>

                                    <div className="mo-card">
                                        <div className="mb-4">
                                            <h3 className="mo-h2">Category Status</h3>
                                            <p className="mt-1 text-sm text-[#A0A0A0]">Green is healthy, yellow is close to the limit, red has crossed it.</p>
                                        </div>
                                        <div className="space-y-4">
                                            {analysis.categories.map((category) => {
                                                const styles = STATUS_STYLES[category.status] || STATUS_STYLES.ON_TRACK;
                                                return (
                                                    <div key={category.name} className={`rounded-2xl border p-4 ${styles.bg} ${styles.border}`}>
                                                        <div className="mb-2 flex items-start justify-between gap-3">
                                                            <div>
                                                                <div className="font-semibold text-white">{category.name}</div>
                                                                <div className="mt-1 text-sm text-[#B8B8B8]">
                                                                    {formatMoney(category.actual)} spent of {formatMoney(category.budgeted)}
                                                                </div>
                                                            </div>
                                                            <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${styles.text} bg-[#09090980]`}>
                                                                {category.status.replace("_", " ")}
                                                            </span>
                                                        </div>
                                                        <div className="h-2 overflow-hidden rounded-full bg-[#1A1A1A]">
                                                            <div
                                                                className="h-full rounded-full transition-all"
                                                                style={{
                                                                    width: `${progressPercent(category.actual, category.budgeted)}%`,
                                                                    backgroundColor: styles.bar,
                                                                }}
                                                            />
                                                        </div>
                                                        <div className="mt-2 flex items-center justify-between text-xs text-[#B8B8B8]">
                                                            <span>{formatPercent(progressPercent(category.actual, category.budgeted))} of budget</span>
                                                            <span>{formatMoney(category.remaining)} remaining</span>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>

                                <div className="mo-card">
                                    <div className="mb-5">
                                        <h3 className="mo-h2">Category Drilldown</h3>
                                        <p className="mt-1 text-sm text-[#A0A0A0]">Review the transactions contributing to each category total.</p>
                                    </div>
                                    <div className="space-y-5">
                                        {analysis.categories.map((category) => {
                                            const styles = STATUS_STYLES[category.status] || STATUS_STYLES.ON_TRACK;
                                            return (
                                                <div key={`${category.name}-transactions`} className="rounded-2xl border border-[#2A2A2A] bg-[#111111] p-4">
                                                    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                                                        <div>
                                                            <div className="flex items-center gap-2">
                                                                <h4 className="text-base font-semibold text-white">{category.name}</h4>
                                                                <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${styles.text} ${styles.bg}`}>
                                                                    {category.status.replace("_", " ")}
                                                                </span>
                                                            </div>
                                                            <div className="mt-2 flex flex-wrap gap-4 text-sm text-[#A0A0A0]">
                                                                <span>Budgeted: <span className="text-white">{formatMoney(category.budgeted)}</span></span>
                                                                <span>Actual: <span className="text-white">{formatMoney(category.actual)}</span></span>
                                                                <span>Remaining: <span className="text-white">{formatMoney(category.remaining)}</span></span>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {category.transactions.length === 0 ? (
                                                        <div className="rounded-xl border border-dashed border-[#2A2A2A] bg-[#0E0E0E] px-4 py-6 text-sm text-[#A0A0A0]">
                                                            No matching expense transactions in this period.
                                                        </div>
                                                    ) : (
                                                        <div className="overflow-hidden rounded-xl border border-[#202020]">
                                                            <div className="max-h-[280px] overflow-auto">
                                                                <table className="w-full text-sm">
                                                                    <thead className="sticky top-0 bg-[#161616]">
                                                                        <tr>
                                                                            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">Date</th>
                                                                            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">Description</th>
                                                                            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">Reference</th>
                                                                            <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wide text-[#8F8F8F]">Amount</th>
                                                                        </tr>
                                                                    </thead>
                                                                    <tbody className="divide-y divide-[#1F1F1F]">
                                                                        {category.transactions.map((transaction) => (
                                                                            <tr key={transaction.id} className="bg-[#101010]">
                                                                                <td className="px-4 py-3 text-[#C8C8C8]">{formatDate(transaction.transactionDate)}</td>
                                                                                <td className="px-4 py-3 text-white">{transaction.description || transaction.category || "Expense transaction"}</td>
                                                                                <td className="px-4 py-3 text-[#A0A0A0]">{transaction.referenceNumber || "—"}</td>
                                                                                <td className="px-4 py-3 text-right font-medium text-white">{formatMoney(transaction.amount)}</td>
                                                                            </tr>
                                                                        ))}
                                                                    </tbody>
                                                                </table>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            ) : null}
        </div>
    );
}
