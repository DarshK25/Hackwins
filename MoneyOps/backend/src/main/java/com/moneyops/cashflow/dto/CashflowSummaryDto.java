package com.moneyops.cashflow.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
public class CashflowSummaryDto {
    private List<MonthlyCashflowDto> monthly;
    private BigDecimal totalIncome;
    private BigDecimal totalExpense;
    private BigDecimal netCashflow;
    private BigDecimal pendingInvoicesTotal;
    private BigDecimal overdueInvoicesTotal;
    private BigDecimal runningBalance;
}
