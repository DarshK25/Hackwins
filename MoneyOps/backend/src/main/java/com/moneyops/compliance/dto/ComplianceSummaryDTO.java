package com.moneyops.compliance.dto;

import lombok.Builder;
import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
public class ComplianceSummaryDTO {
    private long totalInvoices;
    private long paidInvoices;
    private long overdueInvoices;
    private BigDecimal totalGstCollected;
    private double regulatoryCompletenessPercentage;
    private List<String> missingComplianceFields;
}
