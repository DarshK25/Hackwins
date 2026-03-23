package com.moneyops.intelligence;

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
@RequiredArgsConstructor
public class FinanceIntelligenceService {

    private final TransactionService transactionService;
    private final InvoiceService invoiceService;
    private final ClientService clientService;

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

    public MetricsDTO getMetrics(String businessId) {
        MetricsDTO dto = new MetricsDTO();
        try {
            String orgId = OrgContext.getOrgId();
            if (orgId == null) return dto;

            List<TransactionDto> txns = transactionService.getAllTransactions(orgId);
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

            List<InvoiceDto> invoices = invoiceService.getAllInvoices(orgId);
            int totalInvoices = invoices.size();
            int overdueCount = 0;
            BigDecimal overdueAmount = BigDecimal.ZERO;
            int paidCount = 0;

            for (InvoiceDto inv : invoices) {
                if ("OVERDUE".equalsIgnoreCase(inv.getStatus())) {
                    overdueCount++;
                    overdueAmount = overdueAmount.add(inv.getTotalAmount() != null ? inv.getTotalAmount() : BigDecimal.ZERO);
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

            List<TransactionDto> txns = transactionService.getAllTransactions(orgId);
            Map<String, BigDecimal> actualsByCategory = new HashMap<>();
            
            for (TransactionDto t : txns) {
                if ("EXPENSE".equalsIgnoreCase(t.getType())) {
                    String cat = t.getCategory() != null ? t.getCategory() : "UNCATEGORIZED";
                    actualsByCategory.put(cat, actualsByCategory.getOrDefault(cat, BigDecimal.ZERO)
                        .add(t.getAmount() != null ? t.getAmount() : BigDecimal.ZERO));
                }
            }

            BigDecimal totalActual = BigDecimal.ZERO;

            for (Map.Entry<String, BigDecimal> entry : actualsByCategory.entrySet()) {
                BudgetItemDTO item = new BudgetItemDTO();
                item.setCategory(entry.getKey());
                item.setBudgeted(BigDecimal.ZERO);
                item.setActual(entry.getValue());
                item.setVariance(BigDecimal.ZERO.subtract(entry.getValue()));

                if (item.getBudgeted().compareTo(BigDecimal.ZERO) == 0) {
                    item.setStatus("NO_BUDGET");
                } else if (item.getActual().compareTo(item.getBudgeted()) > 0) {
                    item.setStatus("OVER");
                } else {
                    item.setStatus("UNDER");
                }

                dto.getItems().add(item);
                totalActual = totalActual.add(entry.getValue());
            }

            dto.setTotalActual(totalActual);

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
            BigDecimal overdueAmt = metrics.getOverdueAmount();
            double collectionRate = metrics.getCollectionRate();

            LocalDate now = LocalDate.now();
            LocalDate startCurrentMonth = now.withDayOfMonth(1);
            LocalDate startLastMonth = startCurrentMonth.minusMonths(1);
            
            List<TransactionDto> currMonthTxns = transactionService.getTransactionsByDateRange(orgId, startCurrentMonth, now);
            List<TransactionDto> lastMonthTxns = transactionService.getTransactionsByDateRange(orgId, startLastMonth, startCurrentMonth.minusDays(1));

            BigDecimal currMonthRev = BigDecimal.ZERO;
            BigDecimal prevMonthRev = BigDecimal.ZERO;
            BigDecimal currMonthExp = BigDecimal.ZERO;

            for (TransactionDto t : currMonthTxns) {
                if ("INCOME".equalsIgnoreCase(t.getType())) {
                    currMonthRev = currMonthRev.add(t.getAmount() != null ? t.getAmount() : BigDecimal.ZERO);
                } else if ("EXPENSE".equalsIgnoreCase(t.getType())) {
                    currMonthExp = currMonthExp.add(t.getAmount() != null ? t.getAmount() : BigDecimal.ZERO);
                }
            }

            for (TransactionDto t : lastMonthTxns) {
                if ("INCOME".equalsIgnoreCase(t.getType())) {
                    prevMonthRev = prevMonthRev.add(t.getAmount() != null ? t.getAmount() : BigDecimal.ZERO);
                }
            }

            DecimalFormat df = new DecimalFormat("#,##0");

            if (overdueCount > 0) {
                dto.getInsights().add(new InsightItemDTO("CASH_FLOW", "Cash Flow Alert", 
                    overdueCount + " invoices overdue totalling ₹" + df.format(overdueAmt), "HIGH", true));
            }
            if (metrics.getTotalInvoices() > 0) {
                if (collectionRate < 70) {
                    dto.getInsights().add(new InsightItemDTO("COLLECTION", "Collection Rate", 
                        String.format(Locale.US, "%.1f%% of invoices paid on time", collectionRate), "MEDIUM", false));
                } else if (collectionRate >= 90) {
                    dto.getInsights().add(new InsightItemDTO("COLLECTION", "Collection Rate", 
                        String.format(Locale.US, "%.1f%% of invoices paid on time", collectionRate), "LOW", false));
                }
            }
            
            if (currMonthRev.compareTo(prevMonthRev) > 0) {
                dto.getInsights().add(new InsightItemDTO("GROWTH", "Revenue Growth", 
                    "Revenue has increased compared to last month", "LOW", false));
            }
            if (currMonthExp.compareTo(currMonthRev) > 0 && currMonthExp.compareTo(BigDecimal.ZERO) > 0) {
                dto.getInsights().add(new InsightItemDTO("EXPENSE_ALERT", "High Expenses", 
                    "Expenses have exceeded revenue for the current period", "HIGH", true));
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

            List<TransactionDto> txns = transactionService.getAllTransactions(orgId);
            txns.sort((t1, t2) -> {
                LocalDate d1 = t1.getTransactionDate() != null ? t1.getTransactionDate() : LocalDate.MIN;
                LocalDate d2 = t2.getTransactionDate() != null ? t2.getTransactionDate() : LocalDate.MIN;
                return d2.compareTo(d1);
            });

            dto.setTotalEntries(txns.size());

            int count = Math.min(limit, txns.size());
            for (int i = 0; i < count; i++) {
                TransactionDto t = txns.get(i);
                LedgerEntryDTO entry = new LedgerEntryDTO();
                entry.setId(t.getId() != null ? t.getId().toString() : UUID.randomUUID().toString());
                entry.setDate(t.getTransactionDate() != null ? t.getTransactionDate().toString() : "");
                entry.setDescription(t.getDescription() != null ? t.getDescription() : (t.getCategory() != null ? t.getCategory() : "Transaction"));
                entry.setType(t.getType());
                entry.setAmount(t.getAmount() != null ? t.getAmount() : BigDecimal.ZERO);
                entry.setBalance(BigDecimal.ZERO);
                entry.setCategory(t.getCategory());
                
                dto.getEntries().add(entry);
            }

            org.slf4j.LoggerFactory.getLogger(FinanceIntelligenceService.class).info("Computed ledger for businessId: {}", businessId);
            return dto;
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(FinanceIntelligenceService.class).error("Error getting ledger for " + businessId, e);
            return dto;
        }
    }
}
