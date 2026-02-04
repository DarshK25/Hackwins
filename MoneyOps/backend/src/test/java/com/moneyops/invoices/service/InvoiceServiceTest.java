// src/test/java/com/moneyops/invoices/service/InvoiceServiceTest.java
package com.moneyops.invoices.service;

import com.moneyops.invoices.dto.InvoiceDto;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.mapper.InvoiceMapper;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.invoices.repository.InvoiceItemRepository;
import com.moneyops.invoices.validator.InvoiceValidator;
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
    private InvoiceItemRepository invoiceItemRepository;

    @Mock
    private InvoiceMapper invoiceMapper;

    @Mock
    private InvoiceValidator invoiceValidator;

    @InjectMocks
    private InvoiceService invoiceService;

    @Test
    public void testCreateInvoice() {
        UUID orgId = UUID.randomUUID();
        UUID userId = UUID.randomUUID();
        InvoiceDto dto = new InvoiceDto();
        dto.setInvoiceNumber("INV-001");

        Invoice invoice = new Invoice();
        invoice.setId(UUID.randomUUID());

        when(invoiceMapper.toEntity(dto)).thenReturn(invoice);
        when(invoiceRepository.save(any(Invoice.class))).thenReturn(invoice);
        when(invoiceMapper.toDto(invoice)).thenReturn(dto);

        InvoiceDto result = invoiceService.createInvoice(dto, orgId, userId);

        assertNotNull(result);
        verify(invoiceValidator).validate(dto);
        verify(invoiceRepository).save(invoice);
    }

    @Test
    public void testGetInvoiceById() {
        UUID id = UUID.randomUUID();
        UUID orgId = UUID.randomUUID();
        Invoice invoice = new Invoice();
        InvoiceDto dto = new InvoiceDto();

        when(invoiceRepository.findByIdAndOrgId(id, orgId)).thenReturn(Optional.of(invoice));
        when(invoiceMapper.toDto(invoice)).thenReturn(dto);

        InvoiceDto result = invoiceService.getInvoiceById(id, orgId);

        assertNotNull(result);
    }

    @Test
    public void testSendInvoice() {
        UUID id = UUID.randomUUID();
        UUID orgId = UUID.randomUUID();
        Invoice invoice = new Invoice();
        invoice.setStatus(InvoiceStatus.DRAFT);

        when(invoiceRepository.findByIdAndOrgId(id, orgId)).thenReturn(Optional.of(invoice));
        when(invoiceRepository.save(any(Invoice.class))).thenReturn(invoice);
        when(invoiceMapper.toDto(invoice)).thenReturn(new InvoiceDto());

        InvoiceDto result = invoiceService.sendInvoice(id, orgId);

        assertNotNull(result);
        assertEquals(InvoiceStatus.SENT, invoice.getStatus());
    }

    @Test
    public void testMarkPaid() {
        UUID id = UUID.randomUUID();
        UUID orgId = UUID.randomUUID();
        Invoice invoice = new Invoice();
        invoice.setStatus(InvoiceStatus.SENT);

        when(invoiceRepository.findByIdAndOrgId(id, orgId)).thenReturn(Optional.of(invoice));
        when(invoiceRepository.save(any(Invoice.class))).thenReturn(invoice);
        when(invoiceMapper.toDto(invoice)).thenReturn(new InvoiceDto());

        InvoiceDto result = invoiceService.markPaid(id, orgId);

        assertNotNull(result);
        assertEquals(InvoiceStatus.PAID, invoice.getStatus());
        assertNotNull(invoice.getPaymentDate());
    }
}