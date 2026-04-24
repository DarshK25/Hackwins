package com.moneyops.intelligence;

import com.moneyops.clients.dto.ClientDto;
import com.moneyops.clients.service.ClientService;
import com.moneyops.invoices.dto.InvoiceDto;
import com.moneyops.invoices.service.InvoiceService;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.transactions.dto.TransactionDto;
import com.moneyops.transactions.service.TransactionService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AnalyticsReportExportServiceTest {

    @Mock
    private FinanceIntelligenceService financeIntelligenceService;

    @Mock
    private TransactionService transactionService;

    @Mock
    private InvoiceService invoiceService;

    @Mock
    private ClientService clientService;

    @Mock
    private BusinessOrganizationRepository organizationRepository;

    @InjectMocks
    private AnalyticsReportExportService analyticsReportExportService;

    @Test
    void generateOverviewReportProducesPdfBytes() {
        FinanceIntelligenceService.MetricsDTO metrics = new FinanceIntelligenceService.MetricsDTO();
        metrics.setRevenue(new BigDecimal("250000.00"));
        metrics.setExpenses(new BigDecimal("95000.00"));
        metrics.setNetProfit(new BigDecimal("155000.00"));
        metrics.setTotalInvoices(8);
        metrics.setOverdueCount(1);
        metrics.setOverdueAmount(new BigDecimal("12000.00"));
        metrics.setPaidCount(6);
        metrics.setCollectionRate(75.0);

        FinanceIntelligenceService.InsightsDTO insights = new FinanceIntelligenceService.InsightsDTO();
        insights.setInsights(List.of(
                new FinanceIntelligenceService.InsightItemDTO(
                        "COLLECTION",
                        "Improve receivables",
                        "One invoice is overdue and should be followed up this week.",
                        "MEDIUM",
                        true
                )
        ));

        FinanceIntelligenceService.ClientRevenueItemDTO topClient =
                new FinanceIntelligenceService.ClientRevenueItemDTO();
        topClient.setClientId("client-1");
        topClient.setClientName("Acme Ventures");
        topClient.setBilledRevenue(new BigDecimal("175000.00"));
        topClient.setCollectedRevenue(new BigDecimal("140000.00"));
        topClient.setOutstandingRevenue(new BigDecimal("35000.00"));
        topClient.setInvoiceCount(4);
        topClient.setPaidInvoiceCount(3);

        FinanceIntelligenceService.ClientRevenueSummaryDTO clientRevenueSummary =
                new FinanceIntelligenceService.ClientRevenueSummaryDTO();
        clientRevenueSummary.setTopClients(List.of(topClient));
        clientRevenueSummary.setTotalBilledRevenue(new BigDecimal("175000.00"));
        clientRevenueSummary.setTotalCollectedRevenue(new BigDecimal("140000.00"));
        clientRevenueSummary.setTotalClients(1);

        TransactionDto income = new TransactionDto();
        income.setType("INCOME");
        income.setAmount(new BigDecimal("200000.00"));
        income.setCategory("Services");
        income.setTransactionDate(LocalDate.now().minusDays(10));

        TransactionDto expense = new TransactionDto();
        expense.setType("EXPENSE");
        expense.setAmount(new BigDecimal("50000.00"));
        expense.setCategory("Payroll");
        expense.setTransactionDate(LocalDate.now().minusDays(5));

        InvoiceDto invoice = new InvoiceDto();
        invoice.setInvoiceNumber("INV-1001");
        invoice.setClientName("Acme Ventures");
        invoice.setDueDate(LocalDate.now().plusDays(7));
        invoice.setIssueDate(LocalDate.now().minusDays(3));
        invoice.setTotalAmount(new BigDecimal("45000.00"));
        invoice.setStatus("SENT");

        ClientDto client = new ClientDto();
        client.setId("client-1");
        client.setName("Acme Ventures");

        BusinessOrganization organization = new BusinessOrganization();
        organization.setTradingName("MoneyOps Studio");
        organization.setIndustry("Consulting");
        organization.setBusinessType("Private Limited");

        when(financeIntelligenceService.getMetrics("1")).thenReturn(metrics);
        when(financeIntelligenceService.getInsights("1")).thenReturn(insights);
        when(financeIntelligenceService.getClientRevenueSummary("1", 5)).thenReturn(clientRevenueSummary);
        when(transactionService.getAllTransactions("org-1")).thenReturn(List.of(income, expense));
        when(invoiceService.getAllInvoices("org-1")).thenReturn(List.of(invoice));
        when(clientService.getAllClients("org-1")).thenReturn(List.of(client));
        when(organizationRepository.findByIdAndDeletedAtIsNull("org-1")).thenReturn(Optional.of(organization));

        byte[] pdf = analyticsReportExportService.generateOverviewReport("1", "org-1");

        assertTrue(pdf.length > 0);
        assertTrue(analyticsReportExportService.buildOverviewReportFilename("org-1").contains("moneyops-studio"));
    }
}
