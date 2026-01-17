// src/main/java/com/ledgertalk/invoices/controller/InvoiceItemController.java
package com.ledgertalk.invoices.controller;

import com.ledgertalk.invoices.dto.InvoiceItemDto;
import com.ledgertalk.invoices.service.InvoiceService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/invoices/{invoiceId}/items")
@RequiredArgsConstructor
public class InvoiceItemController {

    private final InvoiceService invoiceService;

    @PostMapping
    public ResponseEntity<InvoiceItemDto> addItem(@PathVariable UUID invoiceId,
                                                  @RequestBody InvoiceItemDto itemDto,
                                                  @RequestHeader("X-Org-Id") UUID orgId) {
        InvoiceItemDto added = invoiceService.addItem(invoiceId, itemDto, orgId);
        return ResponseEntity.ok(added);
    }

    @PatchMapping("/{itemId}")
    public ResponseEntity<Void> updateItem(@PathVariable UUID invoiceId,
                                           @PathVariable UUID itemId,
                                           @RequestBody InvoiceItemDto itemDto,
                                           @RequestHeader("X-Org-Id") UUID orgId) {
        invoiceService.updateItem(itemId, itemDto, orgId);
        return ResponseEntity.noContent().build();
    }

    @DeleteMapping("/{itemId}")
    public ResponseEntity<Void> deleteItem(@PathVariable UUID invoiceId,
                                           @PathVariable UUID itemId,
                                           @RequestHeader("X-Org-Id") UUID orgId) {
        invoiceService.deleteItem(itemId, orgId);
        return ResponseEntity.noContent().build();
    }
}