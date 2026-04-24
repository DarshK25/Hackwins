package com.moneyops.expenses.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Data
public class ExpenseSummaryDTO {
    private BigDecimal totalExpenses = BigDecimal.ZERO;
    private List<CategorySummaryDTO> byCategory = new ArrayList<>();
    private List<TrendPointDTO> trend = new ArrayList<>();
    private TopExpenseDTO topExpense;
    private BigDecimal avgMonthly = BigDecimal.ZERO;

    @Data
    public static class CategorySummaryDTO {
        private String category;
        private BigDecimal total = BigDecimal.ZERO;
        private long count = 0;
        private BigDecimal percent = BigDecimal.ZERO;
    }

    @Data
    public static class TrendPointDTO {
        private String month;
        private BigDecimal total = BigDecimal.ZERO;
    }

    @Data
    public static class TopExpenseDTO {
        private String description;
        private BigDecimal amount = BigDecimal.ZERO;
        private LocalDate date;
    }
}
