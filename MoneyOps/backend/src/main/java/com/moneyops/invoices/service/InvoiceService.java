// src/main/java/com/moneyops/invoices/service/InvoiceService.java
package com.moneyops.invoices.service;

import com.moneyops.clients.repository.ClientRepository;
import com.moneyops.invoices.dto.InvoiceDto;
import com.moneyops.invoices.dto.InvoiceItemDto;
import com.moneyops.invoices.entity.Invoice;
import com.moneyops.invoices.entity.InvoiceItem;
import com.moneyops.invoices.entity.InvoiceStatus;
import com.moneyops.invoices.mapper.InvoiceMapper;
import com.moneyops.clients.mapper.ClientMapper;
import com.moneyops.clients.dto.ClientDto;
import com.moneyops.invoices.repository.InvoiceRepository;
import com.moneyops.invoices.validator.InvoiceValidator;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;


@Service
@RequiredArgsConstructor
@Transactional
public class InvoiceService {

    private final InvoiceRepository invoiceRepository;
    private final ClientRepository clientRepository;
    private final InvoiceMapper invoiceMapper;
    private final ClientMapper clientMapper;
    private final InvoiceValidator invoiceValidator;
    private final com.moneyops.audit.service.AuditLogService auditLogService;
    private final com.moneyops.transactions.service.TransactionService transactionService;

    public List<InvoiceDto> getAllInvoices(UUID orgId) {
        var invoices = invoiceRepository.findAllByOrgId(orgId);
        return populateClientDetails(invoices, orgId);
    }

    public void validateAndCalculate(InvoiceDto dto) {
        invoiceValidator.validate(dto);
    }

    public List<InvoiceDto> searchInvoices(UUID orgId, String status, String clientName, int limit) {
        List<Invoice> allInvoices = invoiceRepository.findAllByOrgId(orgId);
        
        // Use a wrapper or just process sequentially to keep it simple and final-safe
        List<Invoice> filtered = allInvoices;

        // 1. Filter by status if provided
        if (status != null && !status.trim().isEmpty()) {
            final String targetStatus = status.toUpperCase();
            filtered = filtered.stream()
                    .filter(inv -> inv.getStatus().name().equals(targetStatus))
                    .collect(Collectors.toList());
        }

        // 2. Filter by client name (Fuzzy Match)
        if (clientName != null && !clientName.trim().isEmpty()) {
            final String query = clientName.toLowerCase().trim();
            var clients = clientRepository.findAllByOrgId(orgId);
            org.apache.commons.text.similarity.JaroWinklerSimilarity similarity = new org.apache.commons.text.similarity.JaroWinklerSimilarity();
            
            var matchedClientIds = clients.stream()
                .filter(c -> similarity.apply(query, c.getName().toLowerCase()) > 0.85)
                .map(com.moneyops.clients.entity.Client::getId)
                .collect(Collectors.toSet());
                
            filtered = filtered.stream()
                .filter(inv -> inv.getClientId() != null && matchedClientIds.contains(inv.getClientId().toString()))
                .collect(Collectors.toList());
        }

        return populateClientDetails(filtered.stream().limit(limit).collect(Collectors.toList()), orgId);
    }

    public InvoiceDto getInvoiceById(String id, UUID orgId) {
        try {
            org.slf4j.LoggerFactory.getLogger(InvoiceService.class).info("Fetching invoice with id [{}] for orgId [{}]", id, orgId);
            
            Invoice invoice = invoiceRepository.findByIdAndOrgId(id, orgId)
                    .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found with id: " + id));

            return populateClientDetails(invoice);
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            org.slf4j.LoggerFactory.getLogger(InvoiceService.class).error("Unexpected error in getInvoiceById for id " + id, e);
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "Error processing invoice: " + e.getMessage());
        }
    }

    public InvoiceDto createInvoice(InvoiceDto dto, UUID orgId, UUID userId) {
        dto.setId(null); 
        invoiceValidator.validate(dto);

        if (dto.getClientId() != null) {
            clientRepository.findById(dto.getClientId().toString()).ifPresentOrElse(client -> {
                if (!client.getOrgId().equals(orgId)) {
                    throw new RuntimeException("Invalid client selected - does not belong to your organization.");
                }
                // Lock in the snapshot data
                dto.setClientName(client.getName());
                dto.setClientEmail(client.getEmail());
                dto.setClientCompany(client.getCompany());
                dto.setClientPhone(client.getPhoneNumber());
            }, () -> {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Client not found.");
            });
        }

        Invoice invoice = invoiceMapper.toEntity(dto);
        invoice.setOrgId(orgId);
        invoice.setCreatedBy(userId);
        
        // Auto-generate invoice number if not provided
        if (invoice.getInvoiceNumber() == null || invoice.getInvoiceNumber().trim().isEmpty()) {
            String dateStamp = java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd").format(java.time.LocalDate.now());
            String randomStr = UUID.randomUUID().toString().substring(0, 4).toUpperCase();
            invoice.setInvoiceNumber("INV-" + dateStamp + "-" + randomStr);
        }

        invoice.setStatus(InvoiceStatus.DRAFT);
        invoice.setCreatedAt(LocalDateTime.now());
        invoice.setUpdatedAt(LocalDateTime.now());

        // Recalculate totals server-side (do not trust frontend)
        recalculateInvoiceTotals(invoice);

        Invoice saved = invoiceRepository.save(invoice);
        return populateClientDetails(saved);
    }

    public InvoiceDto updateInvoice(String id, InvoiceDto dto, UUID orgId) {
        Invoice existing = invoiceRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (existing.getStatus() != InvoiceStatus.DRAFT) {
            throw new IllegalStateException("Can only update draft invoices");
        }

        invoiceValidator.validate(dto);

        Invoice updated = invoiceMapper.toEntity(dto);
        updated.setId(id);
        updated.setOrgId(orgId);
        updated.setCreatedAt(existing.getCreatedAt());
        updated.setCreatedBy(existing.getCreatedBy());
        updated.setUpdatedAt(LocalDateTime.now());

        // Since items are embedded, simply saving the updated invoice includes its items
        Invoice saved = invoiceRepository.save(updated);
        return populateClientDetails(saved);
    }

    public void deleteInvoice(String id, UUID orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (invoice.getStatus() == InvoiceStatus.PAID) {
            throw new IllegalStateException("Cannot delete paid invoices");
        }

        invoiceRepository.deleteByIdAndOrgId(id, orgId);
    }

    public InvoiceDto sendInvoice(String id, UUID orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (invoice.getStatus() != InvoiceStatus.DRAFT) {
            throw new IllegalStateException("Can only send draft invoices");
        }

        invoice.setStatus(InvoiceStatus.SENT);
        invoice.setUpdatedAt(LocalDateTime.now());
        Invoice saved = invoiceRepository.save(invoice);
        return populateClientDetails(saved);
    }

    public InvoiceDto markPaid(String id, UUID orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (invoice.getStatus() != InvoiceStatus.SENT) {
            throw new IllegalStateException("Can only mark sent invoices as paid");
        }

        invoice.setStatus(InvoiceStatus.PAID);
        invoice.setPaymentDate(LocalDate.now());
        invoice.setUpdatedAt(LocalDateTime.now());
        Invoice saved = invoiceRepository.save(invoice);
        return populateClientDetails(saved);
    }

    public List<InvoiceDto> getOverdueInvoices(UUID orgId) {
        List<Invoice> overdue = invoiceRepository.findOverdueByOrgId(orgId, LocalDate.now());
        for (Invoice invoice : overdue) {
            invoice.setStatus(InvoiceStatus.OVERDUE);
            invoiceRepository.save(invoice);
        }
        return populateClientDetails(overdue, orgId);
    }

    // InvoiceItem operations
    public InvoiceItemDto addItem(String invoiceId, InvoiceItemDto itemDto, UUID orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgId(invoiceId, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (invoice.getStatus() != InvoiceStatus.DRAFT) {
            throw new IllegalStateException("Can only add items to draft invoices");
        }

        InvoiceItem item = new InvoiceItem();
        item.setType(InvoiceItem.ItemType.valueOf(itemDto.getType()));
        item.setDescription(itemDto.getDescription());
        item.setQuantity(itemDto.getQuantity());
        item.setRate(itemDto.getRate());
        item.setGstPercent(itemDto.getGstPercent());

        // Calculate line amounts
        var qty = item.getType() == InvoiceItem.ItemType.SERVICE ? 1 : item.getQuantity();
        var lineSubtotal = item.getRate().multiply(BigDecimal.valueOf(qty));
        var lineGst = lineSubtotal.multiply(item.getGstPercent().divide(BigDecimal.valueOf(100)));
        var lineTotal = lineSubtotal.add(lineGst);

        item.setLineSubtotal(lineSubtotal);
        item.setLineGst(lineGst);
        item.setLineTotal(lineTotal);

        if (invoice.getItems() == null) {
            invoice.setItems(new java.util.ArrayList<>());
        }
        invoice.getItems().add(item);

        // Recalculate invoice totals
        recalculateInvoiceTotals(invoice);

        invoiceRepository.save(invoice);
        return invoiceMapper.toItemDto(item);
    }

    public void updateItem(UUID itemId, InvoiceItemDto itemDto, UUID orgId) {
        // Need to find which invoice contains this item
        // In MongoDB we usually know the invoice ID, but if only itemId is provided:
        Invoice invoice = invoiceRepository.findAllByOrgId(orgId).stream()
                .filter(inv -> inv.getItems() != null && inv.getItems().stream().anyMatch(i -> i.getId().equals(itemId)))
                .findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Item not found in any invoice for this org"));

        if (invoice.getStatus() != InvoiceStatus.DRAFT) {
            throw new IllegalStateException("Can only update items in draft invoices");
        }

        InvoiceItem item = invoice.getItems().stream()
                .filter(i -> i.getId().equals(itemId))
                .findFirst()
                .get();

        item.setDescription(itemDto.getDescription());
        item.setQuantity(itemDto.getQuantity());
        item.setRate(itemDto.getRate());
        item.setGstPercent(itemDto.getGstPercent());

        // Recalculate
        var qty = item.getType() == InvoiceItem.ItemType.SERVICE ? 1 : item.getQuantity();
        var lineSubtotal = item.getRate().multiply(BigDecimal.valueOf(qty));
        var lineGst = lineSubtotal.multiply(item.getGstPercent().divide(BigDecimal.valueOf(100)));
        var lineTotal = lineSubtotal.add(lineGst);

        item.setLineSubtotal(lineSubtotal);
        item.setLineGst(lineGst);
        item.setLineTotal(lineTotal);

        // Recalculate invoice totals
        recalculateInvoiceTotals(invoice);
        invoiceRepository.save(invoice);
    }

    public void deleteItem(UUID itemId, UUID orgId) {
        Invoice invoice = invoiceRepository.findAllByOrgId(orgId).stream()
                .filter(inv -> inv.getItems() != null && inv.getItems().stream().anyMatch(i -> i.getId().equals(itemId)))
                .findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Item not found in any invoice for this org"));

        if (invoice.getStatus() != InvoiceStatus.DRAFT) {
            throw new IllegalStateException("Can only delete items from draft invoices");
        }

        invoice.getItems().removeIf(i -> i.getId().equals(itemId));

        // Recalculate invoice totals
        recalculateInvoiceTotals(invoice);
        invoiceRepository.save(invoice);
    }

    private void recalculateInvoiceTotals(Invoice invoice) {
        BigDecimal subtotal = BigDecimal.ZERO;
        BigDecimal gstTotal = BigDecimal.ZERO;
        BigDecimal totalAmount = BigDecimal.ZERO;

        if (invoice.getItems() != null) {
            for (InvoiceItem item : invoice.getItems()) {
                subtotal = subtotal.add(item.getLineSubtotal());
                gstTotal = gstTotal.add(item.getLineGst());
                totalAmount = totalAmount.add(item.getLineTotal());
            }
        }

        invoice.setSubtotal(subtotal);
        invoice.setGstTotal(gstTotal);
        invoice.setTotalAmount(totalAmount);
        invoice.setUpdatedAt(LocalDateTime.now());
    }

    private InvoiceDto populateClientDetails(Invoice invoice) {
        InvoiceDto dto = invoiceMapper.toDto(invoice);
        
        // If snapshot exists, it's already in the DTO from mapping.
        // We only fallback to lookup if snapshot is missing (for legacy data).
        if (dto.getClientName() == null && invoice.getClientId() != null) {
            clientRepository.findById(invoice.getClientId().toString())
                    .ifPresentOrElse(client -> {
                        dto.setClientName(client.getName());
                        dto.setClientEmail(client.getEmail());
                        dto.setClientCompany(client.getCompany());
                        dto.setClientPhone(client.getPhoneNumber());
                    }, () -> {
                        dto.setClientName("Unknown Client (Orphan)");
                    });
        }
        return dto;
    }

    private List<InvoiceDto> populateClientDetails(List<Invoice> invoices, UUID orgId) {
        return invoices.stream()
                .map(this::populateClientDetails)
                .collect(Collectors.toList());
    }

    public List<com.moneyops.audit.entity.AuditLog> getInvoiceLogs(String id, UUID orgId) {
        // First verify ownership
        getInvoiceById(id, orgId);
        return auditLogService.getAuditLogsByEntityId(id);
    }

    public List<com.moneyops.transactions.dto.TransactionDto> getInvoicePayments(String id, UUID orgId) {
        // First verify ownership
        getInvoiceById(id, orgId);
        return transactionService.getTransactionsByInvoice(id, orgId);
    }

    public com.moneyops.transactions.dto.TransactionDto recordPayment(String id, com.moneyops.transactions.dto.TransactionDto paymentDto, UUID orgId, UUID userId) {
        Invoice invoice = invoiceRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));
        
        if (!orgId.equals(invoice.getOrgId())) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Access denied");
        }

        paymentDto.setInvoiceId(id);
        paymentDto.setClientId(invoice.getClientId());
        paymentDto.setType("INCOME");
        if (paymentDto.getCurrency() == null) paymentDto.setCurrency(invoice.getCurrency());
        
        // Ensure transaction date is present for validation
        if (paymentDto.getTransactionDate() == null) {
            paymentDto.setTransactionDate(LocalDate.now());
        }

        com.moneyops.transactions.dto.TransactionDto saved = transactionService.createTransaction(paymentDto, orgId, userId);

        // Update invoice payment info
        invoice.setPaymentDate(paymentDto.getTransactionDate());
        
        // Simple heuristic: if this is the first payment or amount >= total, mark paid
        // In a real system, we'd sum all payments.
        BigDecimal totalPaid = transactionService.getTransactionsByInvoice(id, orgId).stream()
                .map(com.moneyops.transactions.dto.TransactionDto::getAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        
        if (totalPaid.compareTo(invoice.getTotalAmount()) >= 0) {
            invoice.setStatus(InvoiceStatus.PAID);
        } else if (invoice.getStatus() == InvoiceStatus.DRAFT) {
            invoice.setStatus(InvoiceStatus.SENT); // Transition out of draft if payment received
        }

        invoice.setUpdatedAt(LocalDateTime.now());
        invoiceRepository.save(invoice);
        
        return saved;
    }
}
