// src/test/java/com/moneyops/invoices/service/InvoiceServiceTest.java
package com.moneyops.invoices.service;

import com.moneyops.invoices.dto.InvoiceDto;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.mapper.InvoiceMapper;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.invoices.validator.InvoiceValidator;
import com.moneyops.clients.repository.ClientRepository;
import com.moneyops.clients.mapper.ClientMapper;
import com.moneyops.audit.service.AuditLogService;
import com.moneyops.transactions.service.TransactionService;
import com.moneyops.invites.EmailService;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.security.team.TeamActionAuthorizationService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class InvoiceServiceTest {

    @Mock
    private InvoiceRepository invoiceRepository;

    @Mock
    private ClientRepository clientRepository;

    @Mock
    private InvoiceMapper invoiceMapper;

    @Mock
    private ClientMapper clientMapper;

    @Mock
    private InvoiceValidator invoiceValidator;

    @Mock
    private AuditLogService auditLogService;

    @Mock
    private TransactionService transactionService;

    @Mock
    private TeamActionAuthorizationService teamActionAuthorizationService;

    @Mock
    private EmailService emailService;

    @Mock
    private BusinessOrganizationRepository orgRepository;

    @InjectMocks
    private InvoiceService invoiceService;

    @Test
    public void testCreateInvoice() {
        String orgId = UUID.randomUUID().toString();
        String userId = UUID.randomUUID().toString();
        InvoiceDto dto = new InvoiceDto();
        dto.setInvoiceNumber("INV-001");

        Invoice invoice = new Invoice();
        invoice.setId(UUID.randomUUID().toString());
        invoice.setInvoiceNumber("INV-001");

        when(invoiceMapper.toEntity(dto)).thenReturn(invoice);
        when(invoiceRepository.save(any(Invoice.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(invoiceMapper.toDto(any(Invoice.class))).thenReturn(dto);
        when(teamActionAuthorizationService.assertUserCanCreateSensitiveAction(any(), any(), any()))
                .thenReturn(new TeamActionAuthorizationService.CreatorMetadata(userId, "owner@moneyops.test", "OWNER"));

        InvoiceDto result = invoiceService.createInvoice(dto, orgId, userId);

        assertNotNull(result);
        verify(invoiceValidator).validate(dto);
        verify(invoiceRepository).save(any(Invoice.class));
    }

    @Test
    public void testGetInvoiceById() {
        String id = UUID.randomUUID().toString();
        String orgId = UUID.randomUUID().toString();
        Invoice invoice = new Invoice();
        invoice.setOrgId(orgId);
        InvoiceDto dto = new InvoiceDto();

        when(invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)).thenReturn(Optional.of(invoice));
        when(invoiceMapper.toDto(invoice)).thenReturn(dto);

        InvoiceDto result = invoiceService.getInvoiceById(id, orgId);

        assertNotNull(result);
    }

    @Test
    public void testSendInvoice() {
        String id = UUID.randomUUID().toString();
        String orgId = UUID.randomUUID().toString();
        String userId = UUID.randomUUID().toString();
        Invoice invoice = new Invoice();
        invoice.setId(id);
        invoice.setOrgId(orgId);
        invoice.setStatus(InvoiceStatus.DRAFT);
        invoice.setClientEmail("client@example.com");
        invoice.setInvoiceNumber("INV-001");

        InvoiceDto snapshot = new InvoiceDto();
        snapshot.setInvoiceNumber("INV-001");

        when(invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)).thenReturn(Optional.of(invoice));
        when(invoiceRepository.save(any(Invoice.class))).thenReturn(invoice);
        when(invoiceMapper.toEntity(any(InvoiceDto.class))).thenReturn(new Invoice());
        when(teamActionAuthorizationService.assertUserCanCreateSensitiveAction(any(), any(), any()))
                .thenReturn(new TeamActionAuthorizationService.CreatorMetadata(userId, "owner@moneyops.test", "OWNER"));
        when(invoiceMapper.toDto(any(Invoice.class))).thenReturn(snapshot);
        when(orgRepository.findByIdAndDeletedAtIsNull(orgId)).thenReturn(Optional.empty());

        InvoiceDto result = invoiceService.sendInvoice(id, orgId, userId, "123456");

        assertNotNull(result);
        assertEquals(InvoiceStatus.SENT, invoice.getStatus());
        verify(emailService).sendInvoiceEmail(eq("client@example.com"), anyString(), anyString());
    }

    @Test
    public void testMarkPaid() {
        String id = UUID.randomUUID().toString();
        String orgId = UUID.randomUUID().toString();
        Invoice invoice = new Invoice();
        invoice.setId(id);
        invoice.setOrgId(orgId);
        invoice.setStatus(InvoiceStatus.SENT);
        invoice.setTotalAmount(BigDecimal.valueOf(100));

        when(invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)).thenReturn(Optional.of(invoice));
        when(invoiceRepository.save(any(Invoice.class))).thenReturn(invoice);
        when(invoiceMapper.toDto(invoice)).thenReturn(new InvoiceDto());

        InvoiceDto result = invoiceService.markPaid(id, orgId);

        assertNotNull(result);
        assertEquals(InvoiceStatus.PAID, invoice.getStatus());
        assertNotNull(invoice.getPaymentDate());
    }
}
