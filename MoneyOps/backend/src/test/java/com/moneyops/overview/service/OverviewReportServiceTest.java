package com.moneyops.overview.service;

import com.moneyops.clients.entity.Client;
import com.moneyops.clients.repository.ClientRepository;
import com.moneyops.compliance.ComplianceService;
import com.moneyops.compliance.dto.ComplianceSummaryDTO;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.organizations.repository.RegulatoryProfileRepository;
import com.moneyops.overview.dto.OverviewMetricsDTO;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import com.moneyops.transactions.repository.TransactionRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class OverviewReportServiceTest {

    @Mock
    private TransactionRepository transactionRepository;

    @Mock
    private InvoiceRepository invoiceRepository;

    @Mock
    private ClientRepository clientRepository;

    @Mock
    private BusinessOrganizationRepository organizationRepository;

    @Mock
    private RegulatoryProfileRepository regulatoryProfileRepository;

    @Mock
    private ComplianceService complianceService;

    @InjectMocks
    private OverviewReportService overviewReportService;

    @Test
    void getMetricsBuildsLiveSummaryFromRepositories() {
        Transaction income = new Transaction();
        income.setId("txn-1");
        income.setOrgId("org-1");
        income.setType(TransactionType.INCOME);
        income.setAmount(BigDecimal.valueOf(1000));
        income.setTransactionDate(LocalDate.now().withDayOfMonth(5));
        income.setClientId("client-1");

        Transaction expense = new Transaction();
        expense.setId("txn-2");
        expense.setOrgId("org-1");
        expense.setType(TransactionType.EXPENSE);
        expense.setAmount(BigDecimal.valueOf(400));
        expense.setTransactionDate(LocalDate.now().withDayOfMonth(7));

        Invoice overdue = new Invoice();
        overdue.setId("inv-1");
        overdue.setOrgId("org-1");
        overdue.setIssueDate(LocalDate.now().withDayOfMonth(3));
        overdue.setDueDate(LocalDate.now().minusDays(1));
        overdue.setStatus(InvoiceStatus.OVERDUE);
        overdue.setBalanceDue(BigDecimal.valueOf(250));
        overdue.setClientId("client-1");
        overdue.setClientName("Acme Corp");

        Client client = new Client();
        client.setId("client-1");
        client.setOrgId("org-1");
        client.setName("Acme Corp");
        client.setCreatedAt(LocalDateTime.now().minusDays(2));

        BusinessOrganization organization = new BusinessOrganization();
        organization.setId("org-1");
        organization.setLegalName("MoneyOps Labs");
        organization.setIndustry("SaaS");

        ComplianceSummaryDTO complianceSummary = ComplianceSummaryDTO.builder()
                .paidInvoices(0)
                .overdueInvoices(1)
                .regulatoryCompletenessPercentage(80.0)
                .totalGstCollected(BigDecimal.ZERO)
                .build();

        when(transactionRepository.findAllByOrgIdAndDeletedAtIsNull("org-1")).thenReturn(List.of(income, expense));
        when(invoiceRepository.findAllByOrgIdAndDeletedAtIsNull("org-1")).thenReturn(List.of(overdue));
        when(clientRepository.findAllByOrgIdAndDeletedAtIsNull("org-1")).thenReturn(List.of(client));
        when(organizationRepository.findByIdAndDeletedAtIsNull("org-1")).thenReturn(Optional.of(organization));
        when(regulatoryProfileRepository.findByOrgIdAndDeletedAtIsNull("org-1")).thenReturn(Optional.empty());
        when(complianceService.getComplianceSummary("org-1")).thenReturn(complianceSummary);

        OverviewMetricsDTO metrics = overviewReportService.getMetrics("org-1", "monthly");

        assertNotNull(metrics);
        assertEquals("org-1", metrics.getOrgId());
        assertEquals(BigDecimal.valueOf(1000), metrics.getTotalRevenue());
        assertEquals(BigDecimal.valueOf(400), metrics.getTotalExpenses());
        assertEquals(BigDecimal.valueOf(600), metrics.getNetProfitLoss());
        assertEquals(1, metrics.getOutstandingInvoicesCount());
        assertEquals(BigDecimal.valueOf(250), metrics.getOutstandingInvoicesAmount());
        assertEquals(1, metrics.getOverdueInvoicesCount());
        assertEquals(1, metrics.getNewClients());
        assertEquals(1, metrics.getTopClients().size());
        assertEquals("Acme Corp", metrics.getTopClients().get(0).getClientName());
        assertEquals("MoneyOps Labs", metrics.getOrganization().getLegalName());
    }
}
