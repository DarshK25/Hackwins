package com.moneyops.overview.dto;

import com.moneyops.compliance.dto.ComplianceSummaryDTO;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Data
public class OverviewMetricsDTO {

    private String orgId;
    private String period;
    private String reportTitle;
    private LocalDate periodStart;
    private LocalDate periodEnd;
    private OrganizationSummary organization = new OrganizationSummary();
    private BigDecimal totalRevenue = BigDecimal.ZERO;
    private BigDecimal totalExpenses = BigDecimal.ZERO;
    private BigDecimal netProfitLoss = BigDecimal.ZERO;
    private long outstandingInvoicesCount = 0;
    private BigDecimal outstandingInvoicesAmount = BigDecimal.ZERO;
    private long overdueInvoicesCount = 0;
    private BigDecimal overdueInvoicesAmount = BigDecimal.ZERO;
    private long newClients = 0;
    private List<TopClientDTO> topClients = new ArrayList<>();
    private InvoiceStatusBreakdown invoiceStatusBreakdown = new InvoiceStatusBreakdown();
    private List<MonthlyComparisonDTO> monthComparisons = new ArrayList<>();
    private ComplianceSummaryDTO complianceSummary;

    @Data
    public static class OrganizationSummary {
        private String legalName;
        private String tradingName;
        private String businessType;
        private String industry;
        private String primaryEmail;
        private String primaryPhone;
        private String website;
        private String registeredAddress;
        private String currency;
        private String gstNumber;
        private String panNumber;
    }

    @Data
    public static class TopClientDTO {
        private String clientId;
        private String clientName;
        private BigDecimal revenue = BigDecimal.ZERO;
        private long transactionCount = 0;
    }

    @Data
    public static class InvoiceStatusBreakdown {
        private long draft = 0;
        private long sent = 0;
        private long paid = 0;
        private long overdue = 0;
    }

    @Data
    public static class MonthlyComparisonDTO {
        private String label;
        private BigDecimal revenue = BigDecimal.ZERO;
        private BigDecimal expenses = BigDecimal.ZERO;
        private BigDecimal netProfitLoss = BigDecimal.ZERO;
    }
}
