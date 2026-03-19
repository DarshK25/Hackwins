package com.moneyops.invoices.controller;

import com.moneyops.invoices.dto.InvoiceDto;
import com.moneyops.invoices.service.InvoiceService;
import com.moneyops.shared.utils.OrgContext;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/invoices")
@RequiredArgsConstructor
public class InvoiceController {

    private final InvoiceService invoiceService;

    @PostMapping
    public ResponseEntity<InvoiceDto> createInvoice(@RequestBody InvoiceDto dto) {
        UUID orgId = OrgContext.getOrgId();
        UUID userId = OrgContext.getUserId();
        
        if (orgId == null) throw new RuntimeException("Organization context missing");
        
        InvoiceDto created = invoiceService.createInvoice(dto, orgId, userId);
        return ResponseEntity.ok(created);
    }

    @PostMapping("/preview")
    public ResponseEntity<InvoiceDto> previewInvoice(@RequestBody InvoiceDto dto) {
        // Run validation which also calculates totals for items and root DTO
        invoiceService.validateAndCalculate(dto);
        return ResponseEntity.ok(dto);
    }

    @PutMapping("/{id}")
    public ResponseEntity<InvoiceDto> updateInvoice(@PathVariable String id, @RequestBody InvoiceDto dto) {
        UUID orgId = OrgContext.getOrgId();
        InvoiceDto updated = invoiceService.updateInvoice(id, dto, orgId);
        return ResponseEntity.ok(updated);
    }

    @GetMapping
    public ResponseEntity<List<InvoiceDto>> getAllInvoices(
            @RequestParam(required = false) String status,
            @RequestParam(required = false, name = "client_name") String clientName,
            @RequestParam(required = false, name = "clientId") String clientId,
            @RequestParam(defaultValue = "50") int limit) {
        UUID orgId = OrgContext.getOrgId();
        if (orgId == null) return ResponseEntity.ok(List.of());
        List<InvoiceDto> invoices = invoiceService.searchInvoices(orgId, status, clientName, clientId, limit);
        return ResponseEntity.ok(invoices);
    }

    @GetMapping("/{id}")
    public ResponseEntity<InvoiceDto> getInvoice(@PathVariable String id) {
        UUID orgId = OrgContext.getOrgId();
        if (orgId == null) {
            return ResponseEntity.status(403).build(); // Forbidden if context is missing
        }
        InvoiceDto invoice = invoiceService.getInvoiceById(id, orgId);
        return ResponseEntity.ok(invoice);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteInvoice(@PathVariable String id) {
        UUID orgId = OrgContext.getOrgId();
        invoiceService.deleteInvoice(id, orgId);
        return ResponseEntity.noContent().build();
    }

    @PatchMapping("/{id}/send")
    public ResponseEntity<InvoiceDto> sendInvoice(@PathVariable String id) {
        UUID orgId = OrgContext.getOrgId();
        InvoiceDto sent = invoiceService.sendInvoice(id, orgId);
        return ResponseEntity.ok(sent);
    }

    @PatchMapping("/{id}/mark-paid")
    public ResponseEntity<InvoiceDto> markPaid(@PathVariable String id) {
        UUID orgId = OrgContext.getOrgId();
        InvoiceDto paid = invoiceService.markPaid(id, orgId);
        return ResponseEntity.ok(paid);
    }

    @GetMapping("/overdue")
    public ResponseEntity<List<InvoiceDto>> getOverdueInvoices() {
        UUID orgId = OrgContext.getOrgId();
        List<InvoiceDto> overdue = invoiceService.getOverdueInvoices(orgId);
        return ResponseEntity.ok(overdue);
    }

    @GetMapping("/{id}/logs")
    public ResponseEntity<List<com.moneyops.audit.entity.AuditLog>> getInvoiceLogs(@PathVariable String id) {
        UUID orgId = OrgContext.getOrgId();
        return ResponseEntity.ok(invoiceService.getInvoiceLogs(id, orgId));
    }

    @GetMapping("/{id}/payments")
    public ResponseEntity<List<com.moneyops.transactions.dto.TransactionDto>> getInvoicePayments(@PathVariable String id) {
        UUID orgId = OrgContext.getOrgId();
        return ResponseEntity.ok(invoiceService.getInvoicePayments(id, orgId));
    }

    // Alias for frontend mismatch
    @GetMapping("/{id}/payment")
    public ResponseEntity<List<com.moneyops.transactions.dto.TransactionDto>> getInvoicePaymentsSingular(@PathVariable String id) {
        return getInvoicePayments(id);
    }

    @PostMapping("/{id}/payment")
    public ResponseEntity<com.moneyops.shared.dto.ApiResponse<com.moneyops.transactions.dto.TransactionDto>> recordPayment(
            @PathVariable String id,
            @RequestBody com.moneyops.transactions.dto.TransactionDto paymentDto) {
        UUID orgId = OrgContext.getOrgId();
        UUID userId = OrgContext.getUserId();
        com.moneyops.transactions.dto.TransactionDto saved = invoiceService.recordPayment(id, paymentDto, orgId, userId);
        return ResponseEntity.ok(com.moneyops.shared.dto.ApiResponse.success("Payment recorded successfully", saved));
    }
}
