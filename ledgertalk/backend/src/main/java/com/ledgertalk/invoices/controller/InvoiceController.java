// src/main/java/com/ledgertalk/invoices/controller/InvoiceController.java
package com.ledgertalk.invoices.controller;

import com.ledgertalk.invoices.dto.InvoiceDto;
import com.ledgertalk.invoices.service.InvoiceService;
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

    // Assume orgId and userId come from security context or headers
    // For now, pass as headers or params, but in real app, from JWT

    @PostMapping
    public ResponseEntity<InvoiceDto> createInvoice(@RequestBody InvoiceDto dto,
                                                    @RequestHeader("X-Org-Id") UUID orgId,
                                                    @RequestHeader("X-User-Id") UUID userId) {
        InvoiceDto created = invoiceService.createInvoice(dto, orgId, userId);
        return ResponseEntity.ok(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<InvoiceDto> updateInvoice(@PathVariable UUID id,
                                                    @RequestBody InvoiceDto dto,
                                                    @RequestHeader("X-Org-Id") UUID orgId) {
        InvoiceDto updated = invoiceService.updateInvoice(id, dto, orgId);
        return ResponseEntity.ok(updated);
    }

    @PatchMapping("/{id}")
    public ResponseEntity<InvoiceDto> partialUpdateInvoice(@PathVariable UUID id,
                                                           @RequestBody InvoiceDto dto,
                                                           @RequestHeader("X-Org-Id") UUID orgId) {
        // For partial update, only update provided fields
        // But for simplicity, use full update for now
        InvoiceDto updated = invoiceService.updateInvoice(id, dto, orgId);
        return ResponseEntity.ok(updated);
    }

    @GetMapping
    public ResponseEntity<List<InvoiceDto>> getAllInvoices(@RequestHeader("X-Org-Id") UUID orgId) {
        List<InvoiceDto> invoices = invoiceService.getAllInvoices(orgId);
        return ResponseEntity.ok(invoices);
    }

    @GetMapping("/{id}")
    public ResponseEntity<InvoiceDto> getInvoice(@PathVariable UUID id,
                                                 @RequestHeader("X-Org-Id") UUID orgId) {
        InvoiceDto invoice = invoiceService.getInvoiceById(id, orgId);
        return ResponseEntity.ok(invoice);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteInvoice(@PathVariable UUID id,
                                              @RequestHeader("X-Org-Id") UUID orgId) {
        invoiceService.deleteInvoice(id, orgId);
        return ResponseEntity.noContent().build();
    }

    @PatchMapping("/{id}/send")
    public ResponseEntity<InvoiceDto> sendInvoice(@PathVariable UUID id,
                                                  @RequestHeader("X-Org-Id") UUID orgId) {
        InvoiceDto sent = invoiceService.sendInvoice(id, orgId);
        return ResponseEntity.ok(sent);
    }

    @PatchMapping("/{id}/mark-paid")
    public ResponseEntity<InvoiceDto> markPaid(@PathVariable UUID id,
                                               @RequestHeader("X-Org-Id") UUID orgId) {
        InvoiceDto paid = invoiceService.markPaid(id, orgId);
        return ResponseEntity.ok(paid);
    }

    @GetMapping("/overdue")
    public ResponseEntity<List<InvoiceDto>> getOverdueInvoices(@RequestHeader("X-Org-Id") UUID orgId) {
        List<InvoiceDto> overdue = invoiceService.getOverdueInvoices(orgId);
        return ResponseEntity.ok(overdue);
    }
}