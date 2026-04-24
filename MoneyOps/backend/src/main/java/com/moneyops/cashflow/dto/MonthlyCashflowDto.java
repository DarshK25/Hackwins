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
public class MonthlyCashflowDto {
    private String month;
    private BigDecimal income;
    private BigDecimal expense;
    private BigDecimal net;
}
