import { useEffect, useState } from "react";
import { ComplianceDashboard } from "@/components/ComplianceDashboard";
import { Loader2 } from "lucide-react";
import { useAuth } from "@clerk/clerk-react";
import { useOnboardingStatus } from "@/hooks/useOnboardingStatus";
import { useSearchParams } from "react-router-dom";

const BLOCKED_ITC_CATEGORIES = new Set(["SALARIES", "SALARY", "FUEL", "PERSONAL", "RENT"]);
const TDS_194J_CATEGORIES = new Set(["PROFESSIONAL_FEES", "PROFESSIONAL", "CONSULTING"]);
const TDS_194I_CATEGORIES = new Set(["RENT"]);
const TDS_194C_CATEGORIES = new Set(["CONTRACTOR", "SUBCONTRACTOR"]);

function toNumber(value) {
    const num = Number(value || 0);
    return Number.isFinite(num) ? num : 0;
}

function round2(value) {
    return Math.round((value + Number.EPSILON) * 100) / 100;
}

function normalizeCategory(category) {
    return String(category || "").trim().toUpperCase();
}

function formatPeriodDate(value) {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

function deriveInclusiveGst(amount) {
    return round2((toNumber(amount) * 18) / 118);
}

function invoiceInPeriod(invoice, period) {
    return String(invoice.issueDate || "").startsWith(period);
}

function transactionInPeriod(txn, period) {
    const raw = txn.transactionDate || txn.date || txn.createdAt;
    return String(raw || "").slice(0, 7) === period;
}

function isItcClaimable(txn) {
    const gstAmount = toNumber(txn.gstAmount);
    return gstAmount > 0
        && Boolean(txn.itcEligible)
        && Boolean(txn.hasReceipt)
        && Boolean(String(txn.vendorGstin || "").trim())
        && !BLOCKED_ITC_CATEGORIES.has(normalizeCategory(txn.category));
}

function itcExclusionReason(txn) {
    const gstAmount = toNumber(txn.gstAmount);
    if (gstAmount <= 0) return "No GST captured on this expense";
    if (BLOCKED_ITC_CATEGORIES.has(normalizeCategory(txn.category))) return "Category is treated as non-claimable for ITC";
    if (!txn.itcEligible) return "Marked ineligible for ITC";
    if (!String(txn.vendorGstin || "").trim()) return "Vendor GSTIN missing";
    if (!txn.hasReceipt) return "Receipt or tax invoice not marked available";
    return "Excluded from claimable ITC";
}

function determineTdsSection(transactions, annualTotal) {
    const category = normalizeCategory(transactions[0]?.category);
    const hasContractLikeDescription = transactions.some((txn) => {
        const desc = String(txn.description || "").toLowerCase();
        return desc.includes("subcontract") || desc.includes("labour") || desc.includes("contract");
    });
    if (TDS_194J_CATEGORIES.has(category) && annualTotal > 30000) return "194J";
    if (TDS_194I_CATEGORIES.has(category) && annualTotal > 240000) return "194I";
    if ((TDS_194C_CATEGORIES.has(category) || hasContractLikeDescription) && annualTotal > 30000) return "194C";
    return null;
}

function deriveComplianceFallback(invoices, transactions, currentGstSummary = {}, currentTds = {}) {
    const period = currentGstSummary.period || new Date().toISOString().slice(0, 7);
    const monthInvoices = invoices.filter((invoice) => invoiceInPeriod(invoice, period));
    const monthExpenses = transactions.filter((txn) => String(txn.type || "").toUpperCase() === "EXPENSE" && transactionInPeriod(txn, period));

    const invoiceBreakdown = monthInvoices.map((invoice) => {
        const totalAmount = toNumber(invoice.totalAmount);
        const gstAmount = invoice.gstTotal != null ? toNumber(invoice.gstTotal) : deriveInclusiveGst(totalAmount);
        const taxableValue = invoice.subtotal != null ? toNumber(invoice.subtotal) : round2(totalAmount - gstAmount);
        return {
            invoiceId: invoice.id,
            invoiceNumber: invoice.invoiceNumber || invoice.id,
            clientName: invoice.clientName || invoice.clientCompany || "Client",
            issueDate: invoice.issueDate || null,
            status: invoice.status || "",
            taxableValue,
            gstAmount,
            totalAmount,
        };
    });

    const expenseBreakdown = monthExpenses.map((txn) => {
        const grossAmount = toNumber(txn.amount);
        const gstAmount = toNumber(txn.gstAmount);
        const taxableValue = txn.taxableAmount != null ? toNumber(txn.taxableAmount) : round2(grossAmount - gstAmount);
        const claimable = isItcClaimable(txn);
        return {
            transactionId: txn.id,
            description: txn.description || "Expense",
            vendorName: txn.vendorName || txn.vendor || "Unknown vendor",
            category: normalizeCategory(txn.category),
            transactionDate: txn.transactionDate || txn.date || null,
            grossAmount,
            taxableValue,
            gstAmount,
            claimable,
            reason: claimable ? "Included in claimable ITC" : itcExclusionReason(txn),
        };
    });

    const outputTax = round2(invoiceBreakdown.reduce((sum, invoice) => sum + toNumber(invoice.gstAmount), 0));
    const totalTaxableValue = round2(invoiceBreakdown.reduce((sum, invoice) => sum + toNumber(invoice.taxableValue), 0));
    const claimableItc = round2(expenseBreakdown.filter((expense) => expense.claimable).reduce((sum, expense) => sum + toNumber(expense.gstAmount), 0));
    const blockedItc = round2(expenseBreakdown.filter((expense) => toNumber(expense.gstAmount) > 0 && !expense.claimable).reduce((sum, expense) => sum + toNumber(expense.gstAmount), 0));
    const missingGstinItc = round2(expenseBreakdown.filter((expense) => toNumber(expense.gstAmount) > 0 && !BLOCKED_ITC_CATEGORIES.has(expense.category) && !String(monthExpenses.find((txn) => txn.id === expense.transactionId)?.vendorGstin || "").trim()).reduce((sum, expense) => sum + toNumber(expense.gstAmount), 0));
    const netGstPayable = round2(Math.max(0, outputTax - claimableItc));

    const now = new Date();
    const fyStartYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
    const fyStart = new Date(fyStartYear, 3, 1);
    const fyEnd = new Date(fyStartYear + 1, 2, 31);
    const fyExpenses = transactions.filter((txn) => {
        if (String(txn.type || "").toUpperCase() !== "EXPENSE") return false;
        const date = formatPeriodDate(txn.transactionDate || txn.date || txn.createdAt);
        return date && date >= fyStart && date <= fyEnd;
    });
    const vendorMap = new Map();
    fyExpenses.forEach((txn) => {
        const key = txn.vendorName || txn.vendor || txn.description || "Unknown vendor";
        if (!vendorMap.has(key)) vendorMap.set(key, []);
        vendorMap.get(key).push(txn);
    });
    const payableTdsObligations = Array.from(vendorMap.entries()).map(([vendorName, vendorTransactions]) => {
        const annualPayment = round2(vendorTransactions.reduce((sum, txn) => sum + toNumber(txn.amount), 0));
        const section = determineTdsSection(vendorTransactions, annualPayment);
        if (!section) return null;
        const rate = section === "194J" || section === "194I" ? 0.1 : 0.02;
        return {
            vendorName,
            section,
            annualPayment,
            tdsRate: rate,
            tdsAmount: round2(annualPayment * rate),
            transactionIds: vendorTransactions.map((txn) => txn.id).filter(Boolean),
        };
    }).filter(Boolean);
    const totalTdsToDeduct = round2(payableTdsObligations.reduce((sum, item) => sum + toNumber(item.tdsAmount), 0));

    const gstSummary = {
        ...currentGstSummary,
        period,
        invoicesReported: invoiceBreakdown.length,
        totalTaxableValue,
        outputTax,
        claimableItc,
        blockedItc,
        missingGstinItc,
        netGstPayable,
        cgstPayable: round2(netGstPayable / 2),
        sgstPayable: round2(netGstPayable / 2),
        itcRiskCount: expenseBreakdown.filter((expense) => expense.reason === "Vendor GSTIN missing").length,
        invoiceBreakdown,
        expenseBreakdown,
        calculationNotes: currentGstSummary.calculationNotes?.length ? currentGstSummary.calculationNotes : [
            "Fallback breakdown derived from invoices and transactions loaded in the workspace.",
            "Claimable ITC requires GST amount, GSTIN, receipt evidence, and eligible category.",
        ],
    };

    const tdsObligations = {
        ...currentTds,
        payableTdsObligations,
        totalTdsToDeduct,
        calculationNotes: currentTds.calculationNotes?.length ? currentTds.calculationNotes : [
            "Fallback TDS derivation groups expense payments vendor-wise within the current financial year.",
            "Plain hardware purchases are not auto-treated as 194C obligations.",
        ],
    };

    return { gstSummary, tdsObligations };
}

export default function CompliancePage() {
    const [searchParams] = useSearchParams();
    const { getToken } = useAuth();
    const { userId: internalUserId, orgId: internalOrgId, loading: onboardingLoading } = useOnboardingStatus();
    const [isHydrated, setIsHydrated] = useState(false);
    const [businessId] = useState(1);
    const [loading, setLoading] = useState(true);
    const [complianceData, setComplianceData] = useState(null);
    const initialTab = searchParams.get("tab") || "overview";

    async function fetchComplianceStatus() {
        if (!internalUserId || !internalOrgId) {
            setLoading(false);
            return;
        }

        setLoading(true);
        try {
            const token = await getToken();
            const headers = {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`,
                "X-User-Id": internalUserId,
                "X-Org-Id": internalOrgId,
            };
            const responses = await Promise.allSettled([
                fetch(`/api/compliance/status?businessId=${businessId}&userId=${internalUserId}`, { headers }),
                fetch(`/api/compliance/gst/summary`, { headers }),
                fetch(`/api/compliance/tds/obligations`, { headers }),
                fetch(`/api/compliance/audit/readiness`, { headers }),
                fetch(`/api/compliance/issues`, { headers }),
                fetch(`/api/invoices`, { headers }),
                fetch(`/api/transactions`, { headers }),
            ]);
            const [statusResult, gstResult, tdsResult, auditResult, issuesResult, invoicesResult, transactionsResult] = responses;

            const readJson = async (result, fallback) => {
                if (result.status !== "fulfilled" || !result.value.ok) {
                    return fallback;
                }
                return result.value.json();
            };

            const [statusData, gstData, tdsData, auditData, issuesData, invoicesData, transactionsData] = await Promise.all([
                readJson(statusResult, {}),
                readJson(gstResult, {}),
                readJson(tdsResult, {}),
                readJson(auditResult, {}),
                readJson(issuesResult, []),
                readJson(invoicesResult, []),
                readJson(transactionsResult, []),
            ]);

            const normalizedInvoices = Array.isArray(invoicesData) ? invoicesData : invoicesData?.data || [];
            const normalizedTransactions = Array.isArray(transactionsData) ? transactionsData : transactionsData?.transactions || [];
            const fallback = deriveComplianceFallback(normalizedInvoices, normalizedTransactions, gstData, tdsData);
            const finalGstSummary = (!Array.isArray(gstData.invoiceBreakdown) || gstData.invoiceBreakdown.length === 0 || !Array.isArray(gstData.expenseBreakdown) || gstData.expenseBreakdown.length === 0)
                ? fallback.gstSummary
                : gstData;
            const finalTdsObligations = ((!Array.isArray(tdsData.payableTdsObligations) || tdsData.payableTdsObligations.length === 0) && Number(tdsData.totalTdsToDeduct || 0) > 0)
                || (Number(tdsData.totalTdsToDeduct || 0) !== Number(fallback.tdsObligations.totalTdsToDeduct || 0) && Number(fallback.tdsObligations.totalTdsToDeduct || 0) === 0)
                ? fallback.tdsObligations
                : { ...fallback.tdsObligations, ...tdsData, payableTdsObligations: tdsData.payableTdsObligations || fallback.tdsObligations.payableTdsObligations };

            setComplianceData({
                ...statusData,
                gstSummary: finalGstSummary,
                tdsObligations: finalTdsObligations,
                auditReadiness: auditData,
                issues: Array.isArray(issuesData) ? issuesData : [],
            });
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        setIsHydrated(true);
    }, []);

    useEffect(() => {
        if (!onboardingLoading) {
            fetchComplianceStatus();
        }
    }, [onboardingLoading, internalUserId, internalOrgId]);

    if (!isHydrated || loading || onboardingLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-[#4CBB17]" />
            </div>
        );
    }

    return (
        <div className="flex flex-col gap-6">
            <ComplianceDashboard
                businessId={businessId}
                data={complianceData}
                onRefresh={fetchComplianceStatus}
                initialTab={initialTab}
            />
        </div>
    );
}
