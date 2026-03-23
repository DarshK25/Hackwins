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

    public List<InvoiceDto> getAllInvoices(String orgId) {
        if (orgId == null || orgId.isBlank()) throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing organization context");
        var invoices = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
        return populateClientDetails(invoices, orgId);
    }

    public void validateAndCalculate(InvoiceDto dto) {
        invoiceValidator.validate(dto);
    }

    public List<InvoiceDto> searchInvoices(String orgId, String status, String clientName, String clientId, int limit) {
        List<Invoice> allInvoices = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
        
        // Use a wrapper or just process sequentially to keep it simple and final-safe
        List<Invoice> filtered = allInvoices;

        // 1. Filter by status if provided
        if (status != null && !status.trim().isEmpty()) {
            final String targetStatus = status.toUpperCase();
            filtered = filtered.stream()
                    .filter(inv -> inv.getStatus().name().equals(targetStatus))
                    .collect(Collectors.toList());
        }

        // 2. Filter by clientId if provided
        if (clientId != null && !clientId.trim().isEmpty()) {
            filtered = filtered.stream()
                    .filter(inv -> inv.getClientId() != null && inv.getClientId().equals(clientId))
                    .collect(Collectors.toList());
        }

        // 3. Filter by client name (Fuzzy Match) - only if clientId is NOT provided
        if ((clientId == null || clientId.trim().isEmpty()) && clientName != null && !clientName.trim().isEmpty()) {
            final String query = clientName.toLowerCase().trim();
            var clients = clientRepository.findAllByOrgIdAndDeletedAtIsNull(orgId);
            org.apache.commons.text.similarity.JaroWinklerSimilarity similarity = new org.apache.commons.text.similarity.JaroWinklerSimilarity();
            
            var matchedClientIds = clients.stream()
                .filter(c -> similarity.apply(query, c.getName().toLowerCase()) > 0.85)
                .map(com.moneyops.clients.entity.Client::getId)
                .collect(Collectors.toSet());
                
            filtered = filtered.stream()
                .filter(inv -> inv.getClientId() != null && matchedClientIds.contains(inv.getClientId()))
                .collect(Collectors.toList());
        }

        return populateClientDetails(filtered.stream().limit(limit).collect(Collectors.toList()), orgId);
    }

    public InvoiceDto getInvoiceById(String id, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        return populateClientDetails(invoice);
    }

    public InvoiceDto createInvoice(InvoiceDto dto, String orgId, String userId) {
        if (orgId == null || orgId.isBlank()) throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing organization context");
        
        // ✨ Idempotency check 
        if (dto.getIdempotencyKey() != null) {
            var existing = invoiceRepository.findByOrgIdAndInvoiceNumberAndDeletedAtIsNull(orgId, dto.getInvoiceNumber());
            if (existing.isPresent()) return populateClientDetails(existing.get());
        }

        invoiceValidator.validate(dto);

        if (dto.getClientId() != null) {
            clientRepository.findByIdAndOrgIdAndDeletedAtIsNull(dto.getClientId(), orgId).ifPresentOrElse(client -> {
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
        // Balance initialization
        invoice.setAmountPaid(BigDecimal.ZERO);
        invoice.setBalanceDue(BigDecimal.ZERO); // Will be updated by recalculateInvoiceTotals

        // Recalculate totals server-side (do not trust frontend)
        recalculateInvoiceTotals(invoice);

        Invoice saved = invoiceRepository.save(invoice);
        return populateClientDetails(saved);
    }

    public InvoiceDto updateInvoice(String id, InvoiceDto dto, String orgId) {
        Invoice existing = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
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
        updated.setAmountPaid(existing.getAmountPaid()); // Preserve amount paid

        // Since items are embedded, simply saving the updated invoice includes its items
        recalculateInvoiceTotals(updated); // Recalculate totals after item changes
        Invoice saved = invoiceRepository.save(updated);
        return populateClientDetails(saved);
    }

    public void deleteInvoice(String id, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (invoice.getStatus() == InvoiceStatus.PAID) {
            throw new IllegalStateException("Cannot delete paid invoices");
        }

        // ✨ Soft Delete
        invoice.setDeletedAt(LocalDateTime.now());
        invoiceRepository.save(invoice);
    }

    public InvoiceDto sendInvoice(String id, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (invoice.getStatus() != InvoiceStatus.DRAFT) {
            throw new IllegalStateException("Can only send draft invoices");
        }

        invoice.setStatus(InvoiceStatus.SENT);
        invoice.setUpdatedAt(LocalDateTime.now());
        Invoice saved = invoiceRepository.save(invoice);
        return populateClientDetails(saved);
    }

    public InvoiceDto markPaid(String id, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));

        if (invoice.getStatus() != InvoiceStatus.SENT) {
            throw new IllegalStateException("Can only mark sent invoices as paid");
        }

        invoice.setStatus(InvoiceStatus.PAID);
        invoice.setPaymentDate(LocalDate.now());
        invoice.setAmountPaid(invoice.getTotalAmount());
        invoice.setBalanceDue(BigDecimal.ZERO);
        invoice.setUpdatedAt(LocalDateTime.now());
        Invoice saved = invoiceRepository.save(invoice);
        return populateClientDetails(saved);
    }

    public List<InvoiceDto> getOverdueInvoices(String orgId) {
        List<Invoice> overdue = invoiceRepository.findOverdueByOrgId(orgId, LocalDate.now());
        for (Invoice invoice : overdue) {
            invoice.setStatus(InvoiceStatus.OVERDUE);
            invoiceRepository.save(invoice);
        }
        return populateClientDetails(overdue, orgId);
    }

    // InvoiceItem operations
    public InvoiceItemDto addItem(String invoiceId, InvoiceItemDto itemDto, String orgId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(invoiceId, orgId)
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

    public void updateItem(String itemId, InvoiceItemDto itemDto, String orgId) {
        // Need to find which invoice contains this item
        // In MongoDB we usually know the invoice ID, but if only itemId is provided:
        Invoice invoice = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId).stream()
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

    public void deleteItem(String itemId, String orgId) {
        Invoice invoice = invoiceRepository.findAllByOrgIdAndDeletedAtIsNull(orgId).stream()
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
        
        // Update balance due
        BigDecimal paid = invoice.getAmountPaid() != null ? invoice.getAmountPaid() : BigDecimal.ZERO;
        invoice.setBalanceDue(totalAmount.subtract(paid));
        invoice.setUpdatedAt(LocalDateTime.now());
    }

    private InvoiceDto populateClientDetails(Invoice invoice) {
        InvoiceDto dto = invoiceMapper.toDto(invoice);
        
        // If snapshot exists, it's already in the DTO from mapping.
        // We only fallback to lookup if snapshot is missing (for legacy data).
        if (dto.getClientName() == null && invoice.getClientId() != null) {
            clientRepository.findByIdAndOrgIdAndDeletedAtIsNull(invoice.getClientId(), invoice.getOrgId())
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

    private List<InvoiceDto> populateClientDetails(List<Invoice> invoices, String orgId) {
        return invoices.stream()
                .map(this::populateClientDetails)
                .collect(Collectors.toList());
    }

    public List<com.moneyops.audit.entity.AuditLog> getInvoiceLogs(String id, String orgId) {
        // First verify ownership
        getInvoiceById(id, orgId);
        return auditLogService.getAuditLogsByEntityId(id);
    }

    public List<com.moneyops.transactions.dto.TransactionDto> getInvoicePayments(String id, String orgId) {
        // First verify ownership
        getInvoiceById(id, orgId);
        return transactionService.getTransactionsByInvoice(id, orgId);
    }

    public com.moneyops.transactions.dto.TransactionDto recordPayment(String id, com.moneyops.transactions.dto.TransactionDto paymentDto, String orgId, String userId) {
        Invoice invoice = invoiceRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Invoice not found"));
        
        paymentDto.setInvoiceId(id);
        paymentDto.setClientId(invoice.getClientId());
        paymentDto.setType("INCOME");
        if (paymentDto.getCurrency() == null) paymentDto.setCurrency(invoice.getCurrency());
        
        // Ensure transaction date is present for validation
        if (paymentDto.getTransactionDate() == null) {
            paymentDto.setTransactionDate(LocalDate.now());
        }

        // ✨ We don't call transactionService here if we want to avoid double-processing, 
        // but transactionService is where the DB write happens.
        com.moneyops.transactions.dto.TransactionDto saved = transactionService.createTransaction(paymentDto, orgId, userId);

        // ✨ Denormalized sync
        BigDecimal paid = invoice.getAmountPaid() != null ? invoice.getAmountPaid() : BigDecimal.ZERO;
        invoice.setAmountPaid(paid.add(paymentDto.getAmount()));
        invoice.setBalanceDue(invoice.getTotalAmount().subtract(invoice.getAmountPaid()));
        
        if (invoice.getBalanceDue().compareTo(BigDecimal.ZERO) <= 0) {
            invoice.setStatus(InvoiceStatus.PAID);
            invoice.setPaymentDate(paymentDto.getTransactionDate());
        } else if (invoice.getStatus() == InvoiceStatus.DRAFT) {
            invoice.setStatus(InvoiceStatus.SENT); // Transition out of draft if payment received
        }

        invoice.setUpdatedAt(LocalDateTime.now());
        invoiceRepository.save(invoice);
        
        return saved;
    }
}
