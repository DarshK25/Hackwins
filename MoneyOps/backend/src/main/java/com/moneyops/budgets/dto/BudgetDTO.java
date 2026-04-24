package com.moneyops.budgets.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
public class BudgetDTO {

    private String id;
    private String orgId;
    private String name;
    private String period;
    private LocalDate startDate;
    private LocalDate endDate;
    private List<CategoryDTO> categories = new ArrayList<>();
    private BigDecimal totalBudget = BigDecimal.ZERO;
    private BigDecimal totalSpent = BigDecimal.ZERO;
    private BigDecimal remaining = BigDecimal.ZERO;
    private BigDecimal utilizationPercent = BigDecimal.ZERO;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    @Data
    public static class CategoryDTO {
        private String name;
        private BigDecimal limit = BigDecimal.ZERO;
        private BigDecimal actual = BigDecimal.ZERO;
        private BigDecimal remaining = BigDecimal.ZERO;
        private String status = "ON_TRACK";
    }
}
