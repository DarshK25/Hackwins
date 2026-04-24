package com.moneyops.budgets.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Data
public class BudgetAnalysisDTO {

    private String budgetId;
    private String orgId;
    private String name;
    private String period;
    private LocalDate startDate;
    private LocalDate endDate;
    private BigDecimal totalBudget = BigDecimal.ZERO;
    private BigDecimal totalSpent = BigDecimal.ZERO;
    private BigDecimal remaining = BigDecimal.ZERO;
    private BigDecimal utilizationPercent = BigDecimal.ZERO;
    private List<CategoryAnalysisDTO> categories = new ArrayList<>();

    @Data
    public static class CategoryAnalysisDTO {
        private String name;
        private BigDecimal budgeted = BigDecimal.ZERO;
        private BigDecimal actual = BigDecimal.ZERO;
        private BigDecimal remaining = BigDecimal.ZERO;
        private String status = "ON_TRACK";
        private List<TransactionSummaryDTO> transactions = new ArrayList<>();
    }

    @Data
    public static class TransactionSummaryDTO {
        private String id;
        private LocalDate transactionDate;
        private String description;
        private BigDecimal amount = BigDecimal.ZERO;
        private String category;
        private String referenceNumber;
    }
}
