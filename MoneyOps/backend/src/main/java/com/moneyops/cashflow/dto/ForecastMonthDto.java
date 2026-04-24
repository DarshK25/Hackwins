package com.moneyops.cashflow.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ForecastMonthDto {
    private String month;
    private BigDecimal predictedIncome;
    private BigDecimal predictedExpense;
    private double confidence;
}
