package com.moneyops.cashflow.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class CashflowForecastDto {
    private List<ForecastMonthDto> forecast;
}
