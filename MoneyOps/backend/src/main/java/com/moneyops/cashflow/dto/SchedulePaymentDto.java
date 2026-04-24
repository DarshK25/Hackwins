package com.moneyops.cashflow.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
public class SchedulePaymentDto {
    private String orgId;
    private String invoiceId;
    private LocalDate scheduledDate;
    private BigDecimal amount;
    private String paymentMethod;
    private String notes;
}
