package com.moneyops.intelligence;

import com.moneyops.budget.service.BudgetService;
import com.moneyops.invoices.dto.InvoiceDto;
import com.moneyops.invoices.service.InvoiceService;
import com.moneyops.transactions.dto.TransactionDto;
import com.moneyops.transactions.service.TransactionService;
import com.moneyops.clients.service.ClientService;
import com.moneyops.shared.utils.OrgContext;
import lombok.RequiredArgsConstructor;
import lombok.Data;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.text.DecimalFormat;
import java.time.LocalDate;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class FinanceIntelligenceService {

    private final TransactionService transactionService;
    private final InvoiceService invoiceService;
    private final ClientService clientService;
    private final BudgetService budgetService;

    public FinanceIntelligenceService(TransactionService transactionService, InvoiceService invoiceService, 
                                       ClientService clientService, BudgetService budgetService) {
        this.transactionService = transactionService;
        this.invoiceService = invoiceService;
        this.clientService = clientService;
        this.budgetService = budgetService;
    }

    @Data
    public static class MetricsDTO {
        private BigDecimal revenue = BigDecimal.ZERO;
        private BigDecimal expenses = BigDecimal.ZERO;
        private BigDecimal netProfit = BigDecimal.ZERO;
        private int totalInvoices = 0;
        private int overdueCount = 0;
        private BigDecimal overdueAmount = BigDecimal.ZERO;
        private int paidCount = 0;
        private double collectionRate = 0.0;
        private String period = "CURRENT_MONTH";
    }

    @Data
    public static class BudgetItemDTO {
        private String category;
        private BigDecimal budgeted = BigDecimal.ZERO;
        private BigDecimal actual = BigDecimal.ZERO;
        private BigDecimal variance = BigDecimal.ZERO;
        private String status;
    }

    @Data
    public static class BudgetDTO {
        private List<BudgetItemDTO> items = new ArrayList<>();
        private BigDecimal totalBudgeted = BigDecimal.ZERO;
        private BigDecimal totalActual = BigDecimal.ZERO;
    }

    @Data
    public static class InsightItemDTO {
        private String type;
        private String title;
        private String description;
        private String severity;
        private boolean actionable;
        
        public InsightItemDTO(String type, String title, String description, String severity, boolean actionable) {
            this.type = type;
            this.title = title;
            this.description = description;
            this.severity = severity;
            this.actionable = actionable;
        }
    }

    @Data
    public static class InsightsDTO {
        private List<InsightItemDTO> insights = new ArrayList<>();
    }

    @Data
    public static class LedgerEntryDTO {
        private String id;
        private String date;
        private String description;
        private String type;
        private BigDecimal amount;
        private BigDecimal balance;
        private String category;
    }

    @Data
    public static class LedgerDTO {
        private List<LedgerEntryDTO> entries = new ArrayList<>();
        private int totalEntries = 0;
    }

    private BigDecimal safeAmount(BigDecimal value) {
        return value != null ? value : BigDecimal.ZERO;
    }

    private BigDecimal computeOutstanding(InvoiceDto invoice) {
        BigDecimal total = safeAmount(invoice.getTotalAmount());
        BigDecimal paid = safeAmount(invoice.getAmountPaid());
        BigDecimal balanceDue = invoice.getBalanceDue();
        if (balanceDue != null && balanceDue.compareTo(BigDecimal.ZERO) >= 0 && balanceDue.compareTo(total) <= 0) {
            return balanceDue;
        }
        return total.subtract(paid).max(BigDecimal.ZERO);
    }

    private String formatInr(BigDecimal value) {
        DecimalFormat df = new DecimalFormat("#,##0");
        return "₹" + df.format(safeAmount(value));
    }

    public MetricsDTO getMetrics(String businessId) {
        MetricsDTO dto = new MetricsDTO();
        try {
            String orgId = OrgContext.getOrgId();
            if (orgId == null) return dto;

            LocalDate endDate = LocalDate.now();
            LocalDate startDate = endDate.minusDays(89);
            List<TransactionDto> txns = transactionService.getTransactionsByDateRange(orgId, startDate, endDate);
            BigDecimal revenue = BigDecimal.ZERO;
            BigDecimal expenses = BigDecimal.ZERO;
            for (TransactionDto t : txns) {
                if ("INCOME".equalsIgnoreCase(t.getType())) {
                    revenue = revenue.add(t.getAmount() != null ? t.getAmount() : BigDecimal.ZERO);
                } else if ("EXPENSE".equalsIgnoreCase(t.getType())) {
                    expenses = expenses.add(t.getAmount() != null ? t.getAmount() : BigDecimal.ZERO);
                }
            }
            
            dto.setRevenue(revenue);
            dto.setExpenses(expenses);
            dto.setNetProfit(revenue.subtract(expenses));
            dto.setPeriod("LAST_90_DAYS");

            List<InvoiceDto> invoices = invoiceService.getAllInvoices(orgId);
            int totalInvoices = invoices.size();
            int overdueCount = 0;
            BigDecimal overdueAmount = BigDecimal.ZERO;
            int paidCount = 0;

            for (InvoiceDto inv : invoices) {
                if ("OVERDUE".equalsIgnoreCase(inv.getStatus())) {
                    overdueCount++;
                    BigDecimal outstanding = computeOutstanding(inv);
                    if (outstanding.compareTo(BigDecimal.ZERO) > 0) {
                        overdueAmount = overdueAmount.add(outstanding);
                    }
                } else if ("PAID".equalsIgnoreCase(inv.getStatus())) {
                    paidCount++;
                }
            }

            dto.setTotalInvoices(totalInvoices);
            dto.setOverdueCount(overdueCount);
            dto.setOverdueAmount(overdueAmount);
            dto.setPaidCount(paidCount);

            if (totalInvoices > 0) {
                double rate = ((double) paidCount / totalInvoices) * 100.0;
                dto.setCollectionRate(Math.round(rate * 10.0) / 10.0);
            }

            org.slf4j.LoggerFactory.getLogger(FinanceIntelligenceService.class).info("Computed metrics for businessId: {}", businessId);
            return dto;
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(FinanceIntelligenceService.class).error("Error getting metrics for " + businessId, e);
            return dto;
        }
    }

    public BudgetDTO getBudget(String businessId) {
        BudgetDTO dto = new BudgetDTO();
        try {
            String orgId = OrgContext.getOrgId();
            if (orgId == null) return dto;

            LocalDate now = LocalDate.now();
            int year = now.getYear();
            int month = now.getMonthValue();

            List<com.moneyops.budget.entity.Budget> budgets = budgetService.getBudgetsForMonth(orgId, year, month);
            Map<String, BigDecimal> budgetByCategory = new HashMap<>();
            for (com.moneyops.budget.entity.Budget b : budgets) {
                budgetByCategory.put(b.getCategory().toUpperCase(), b.getAmount());
            }

            // Filter transactions to the current month only for accurate budget comparison
            LocalDate monthStart = now.withDayOfMonth(1);
            LocalDate monthEnd = now.withDayOfMonth(now.lengthOfMonth());
            List<TransactionDto> txns = transactionService.getTransactionsByDateRange(orgId, monthStart, monthEnd);
            Map<String, BigDecimal> actualsByCategory = new HashMap<>();
            
            for (TransactionDto t : txns) {
                if ("EXPENSE".equalsIgnoreCase(t.getType())) {
                    String cat = (t.getCategory() != null && !t.getCategory().isBlank()) 
                        ? t.getCategory().toUpperCase() 
                        : "UNCATEGORIZED";
                    actualsByCategory.put(cat, actualsByCategory.getOrDefault(cat, BigDecimal.ZERO)
                        .add(t.getAmount() != null ? t.getAmount() : BigDecimal.ZERO));
                }
            }

            Set<String> allCategories = new HashSet<>(budgetByCategory.keySet());
            allCategories.addAll(actualsByCategory.keySet());

            // If no budgets or transactions yet, provide some standard categories as baseline
            if (allCategories.isEmpty()) {
                allCategories.addAll(Arrays.asList("MARKETING", "OPERATIONS", "SOFTWARE", "PAYROLL", "HARDWARE"));
            }

            BigDecimal totalActual = BigDecimal.ZERO;
            BigDecimal totalBudgeted = BigDecimal.ZERO;

            for (String rawCategory : allCategories) {
                BudgetItemDTO item = new BudgetItemDTO();
                // Normalise category name for UI
                String normalizedCat = rawCategory.charAt(0) + rawCategory.substring(1).toLowerCase();
                item.setCategory(normalizedCat);
                
                BigDecimal budgeted = budgetByCategory.getOrDefault(rawCategory, BigDecimal.ZERO);
                BigDecimal actual = actualsByCategory.getOrDefault(rawCategory, BigDecimal.ZERO);
                item.setBudgeted(budgeted);
                item.setActual(actual);
                item.setVariance(budgeted.subtract(actual));

                if (budgeted.compareTo(BigDecimal.ZERO) == 0) {
                    item.setStatus("NO_BUDGET");
                } else if (actual.compareTo(budgeted) > 0) {
                    item.setStatus("OVER");
                } else {
                    item.setStatus("UNDER");
                }

                dto.getItems().add(item);
                totalActual = totalActual.add(actual);
                totalBudgeted = totalBudgeted.add(budgeted);
            }

            dto.setTotalActual(totalActual);
            dto.setTotalBudgeted(totalBudgeted);

            org.slf4j.LoggerFactory.getLogger(FinanceIntelligenceService.class).info("Computed budget for businessId: {}", businessId);
            return dto;
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(FinanceIntelligenceService.class).error("Error getting budget for " + businessId, e);
            return dto;
        }
    }

    public InsightsDTO getInsights(String businessId) {
        InsightsDTO dto = new InsightsDTO();
        try {
            String orgId = OrgContext.getOrgId();
            if (orgId == null) return dto;

            MetricsDTO metrics = getMetrics(businessId);
            int overdueCount = metrics.getOverdueCount();
            double collectionRate = metrics.getCollectionRate();

            LocalDate now = LocalDate.now();
            LocalDate startLast90Days = now.minusDays(89);
            LocalDate startCurrentMonth = now.withDayOfMonth(1);
            LocalDate startLastMonth = startCurrentMonth.minusMonths(1);
            List<InvoiceDto> invoices = invoiceService.getAllInvoices(orgId);
            List<InvoiceDto> overdueInvoices = invoices.stream()
                    .filter(inv -> "OVERDUE".equalsIgnoreCase(inv.getStatus()))
                    .sorted(Comparator.comparing(this::computeOutstanding).reversed())
                    .toList();

            BigDecimal overdueAmt = overdueInvoices.stream()
                    .map(this::computeOutstanding)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);

            List<TransactionDto> trailingTxns = transactionService.getTransactionsByDateRange(orgId, startLast90Days, now);
            List<TransactionDto> currMonthTxns = transactionService.getTransactionsByDateRange(orgId, startCurrentMonth, now);
            List<TransactionDto> lastMonthTxns = transactionService.getTransactionsByDateRange(orgId, startLastMonth, startCurrentMonth.minusDays(1));

            BigDecimal currMonthRev = BigDecimal.ZERO;
            BigDecimal prevMonthRev = BigDecimal.ZERO;
            BigDecimal currMonthExp = BigDecimal.ZERO;
            BigDecimal trailingRevenue = BigDecimal.ZERO;
            BigDecimal trailingExpenses = BigDecimal.ZERO;
            Map<String, BigDecimal> expenseByCategory = new HashMap<>();

            for (TransactionDto t : currMonthTxns) {
                if ("INCOME".equalsIgnoreCase(t.getType())) {
                    currMonthRev = currMonthRev.add(safeAmount(t.getAmount()));
                } else if ("EXPENSE".equalsIgnoreCase(t.getType())) {
                    currMonthExp = currMonthExp.add(safeAmount(t.getAmount()));
                }
            }

            for (TransactionDto t : lastMonthTxns) {
                if ("INCOME".equalsIgnoreCase(t.getType())) {
                    prevMonthRev = prevMonthRev.add(safeAmount(t.getAmount()));
                }
            }

            for (TransactionDto t : trailingTxns) {
                if ("INCOME".equalsIgnoreCase(t.getType())) {
                    trailingRevenue = trailingRevenue.add(safeAmount(t.getAmount()));
                } else if ("EXPENSE".equalsIgnoreCase(t.getType())) {
                    BigDecimal amount = safeAmount(t.getAmount());
                    trailingExpenses = trailingExpenses.add(amount);
                    String category = (t.getCategory() != null && !t.getCategory().isBlank())
                            ? t.getCategory().toLowerCase(Locale.ROOT)
                            : "uncategorized";
                    expenseByCategory.merge(category, amount, BigDecimal::add);
                }
            }

            Optional<Map.Entry<String, BigDecimal>> topExpenseCategory = expenseByCategory.entrySet().stream()
                    .max(Map.Entry.comparingByValue());
            BigDecimal collectionGap = trailingExpenses.subtract(trailingRevenue).max(BigDecimal.ZERO);

            if (overdueCount > 0) {
                InvoiceDto largestOverdue = overdueInvoices.isEmpty() ? null : overdueInvoices.get(0);
                String focusClient = largestOverdue != null ? largestOverdue.getClientName() : "your largest debtor";
                BigDecimal focusAmount = largestOverdue != null ? computeOutstanding(largestOverdue) : BigDecimal.ZERO;
                dto.getInsights().add(new InsightItemDTO(
                        "CASH_FLOW",
                        "Working Capital Pressure",
                        overdueCount + " overdue invoices are blocking " + formatInr(overdueAmt)
                                + ". Start with " + focusClient + " at " + formatInr(focusAmount)
                                + " and move large accounts to milestone-based collection follow-ups.",
                        "HIGH",
                        true
                ));
            }

            if (metrics.getTotalInvoices() > 0) {
                if (collectionRate < 70) {
                    String collectionMessage = String.format(Locale.US,
                            "%.1f%% of invoices are paid on time. Collections are too weak to fund project execution without constant cash strain.",
                            collectionRate);
                    dto.getInsights().add(new InsightItemDTO("COLLECTION", "Collection Discipline", collectionMessage, "HIGH", true));
                } else if (collectionRate >= 90) {
                    dto.getInsights().add(new InsightItemDTO("COLLECTION", "Collection Rate",
                            String.format(Locale.US, "%.1f%% of invoices are paid on time", collectionRate), "LOW", false));
                }
            }

            if (collectionGap.compareTo(BigDecimal.ZERO) > 0) {
                dto.getInsights().add(new InsightItemDTO(
                        "OPERATIONS",
                        "Execution Spend Is Ahead Of Collections",
                        "Over the last 90 days, expenses are ahead of realised income by " + formatInr(collectionGap)
                                + ". For VoltNest, that means hardware and installation costs are being funded before customer cash arrives.",
                        "HIGH",
                        true
                ));
            }

            if (topExpenseCategory.isPresent() && trailingExpenses.compareTo(BigDecimal.ZERO) > 0) {
                Map.Entry<String, BigDecimal> topCategory = topExpenseCategory.get();
                BigDecimal share = topCategory.getValue()
                        .multiply(BigDecimal.valueOf(100))
                        .divide(trailingExpenses, 0, java.math.RoundingMode.HALF_UP);
                if (share.compareTo(BigDecimal.valueOf(35)) >= 0) {
                    dto.getInsights().add(new InsightItemDTO(
                            "COST_STRUCTURE",
                            "Hardware Is Driving The Cost Base",
                            topCategory.getKey() + " is " + share + "% of spend at " + formatInr(topCategory.getValue())
                                    + ". Negotiate supplier credit and align procurement with invoice milestones before approving the next bulk order.",
                            "MEDIUM",
                            true
                    ));
                }
            }

            if (currMonthRev.compareTo(prevMonthRev) > 0) {
                dto.getInsights().add(new InsightItemDTO("GROWTH", "Revenue Growth",
                    "Collections improved compared to last month, but the gain is still being absorbed by execution-heavy operating costs.", "LOW", false));
            }
            if (currMonthExp.compareTo(currMonthRev) > 0 && currMonthExp.compareTo(BigDecimal.ZERO) > 0) {
                dto.getInsights().add(new InsightItemDTO("EXPENSE_ALERT", "Current Month Burn",
                    "Current-period expenses are ahead of current-period collections. Delay non-essential discretionary spend until overdue invoices convert into cash.", "HIGH", true));
            }

            if (!expenseByCategory.isEmpty() && budgetService.getBudgetsForMonth(orgId, now.getYear(), now.getMonthValue()).isEmpty()) {
                dto.getInsights().add(new InsightItemDTO(
                        "CONTROL",
                        "No Expense Baseline Is Configured",
                        "The finance model is tracking actual spend but has no budget guardrails yet. Set monthly caps for hardware, payroll, and travel so overruns show up before cash gets tight.",
                        "MEDIUM",
                        true
                ));
            }

            org.slf4j.LoggerFactory.getLogger(FinanceIntelligenceService.class).info("Computed insights for businessId: {}", businessId);
            return dto;
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(FinanceIntelligenceService.class).error("Error getting insights for " + businessId, e);
            return dto;
        }
    }

    public LedgerDTO getLedger(String businessId, int limit) {
        LedgerDTO dto = new LedgerDTO();
        try {
            String orgId = OrgContext.getOrgId();
            if (orgId == null) return dto;

            LocalDate endDate = LocalDate.now();
            LocalDate startDate = endDate.minusDays(29);
            List<TransactionDto> txns = transactionService.getTransactionsByDateRange(orgId, startDate, endDate);
            txns.sort((t1, t2) -> {
                LocalDate d1 = t1.getTransactionDate() != null ? t1.getTransactionDate() : LocalDate.MIN;
                LocalDate d2 = t2.getTransactionDate() != null ? t2.getTransactionDate() : LocalDate.MIN;
                if (d1.equals(d2)) {
                    String id1 = t1.getId() != null ? t1.getId() : "";
                    String id2 = t2.getId() != null ? t2.getId() : "";
                    return id1.compareTo(id2);
                }
                return d1.compareTo(d2);
            });

            BigDecimal runningBalance = BigDecimal.ZERO;
            List<LedgerEntryDTO> allEntries = new ArrayList<>();
            for (TransactionDto t : txns) {
                BigDecimal amount = t.getAmount() != null ? t.getAmount() : BigDecimal.ZERO;
                if ("INCOME".equalsIgnoreCase(t.getType())) {
                    runningBalance = runningBalance.add(amount);
                } else if ("EXPENSE".equalsIgnoreCase(t.getType())) {
                    runningBalance = runningBalance.subtract(amount);
                }

                LedgerEntryDTO entry = new LedgerEntryDTO();
                entry.setId(t.getId() != null ? t.getId().toString() : UUID.randomUUID().toString());
                entry.setDate(t.getTransactionDate() != null ? t.getTransactionDate().toString() : "");
                entry.setDescription(t.getDescription() != null ? t.getDescription() : (t.getCategory() != null ? t.getCategory() : "Transaction"));
                entry.setType(t.getType());
                entry.setAmount(amount);
                entry.setBalance(runningBalance);
                entry.setCategory(t.getCategory());

                allEntries.add(entry);
            }

            allEntries.sort((e1, e2) -> {
                LocalDate d1 = (e1.getDate() != null && !e1.getDate().isBlank()) ? LocalDate.parse(e1.getDate()) : LocalDate.MIN;
                LocalDate d2 = (e2.getDate() != null && !e2.getDate().isBlank()) ? LocalDate.parse(e2.getDate()) : LocalDate.MIN;
                return d2.compareTo(d1);
            });

            dto.setTotalEntries(allEntries.size());

            int count = Math.min(limit, allEntries.size());
            for (int i = 0; i < count; i++) {
                dto.getEntries().add(allEntries.get(i));
            }

            org.slf4j.LoggerFactory.getLogger(FinanceIntelligenceService.class).info("Computed ledger for businessId: {}", businessId);
            return dto;
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(FinanceIntelligenceService.class).error("Error getting ledger for " + businessId, e);
            return dto;
        }
    }
}
