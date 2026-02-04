// src/main/java/com/moneyops/transactions/controller/TransactionController.java
package com.moneyops.transactions.controller;

import com.moneyops.transactions.dto.TransactionDto;
import com.moneyops.transactions.service.TransactionService;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/transactions")
@RequiredArgsConstructor
public class TransactionController {

    private final TransactionService transactionService;

    @PostMapping
    public ResponseEntity<TransactionDto> createTransaction(@RequestBody TransactionDto dto,
                                                            @RequestHeader("X-Org-Id") UUID orgId,
                                                            @RequestHeader("X-User-Id") UUID userId) {
        TransactionDto created = transactionService.createTransaction(dto, orgId, userId);
        return ResponseEntity.ok(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<TransactionDto> updateTransaction(@PathVariable UUID id,
                                                            @RequestBody TransactionDto dto,
                                                            @RequestHeader("X-Org-Id") UUID orgId) {
        TransactionDto updated = transactionService.updateTransaction(id, dto, orgId);
        return ResponseEntity.ok(updated);
    }

    @GetMapping
    public ResponseEntity<List<TransactionDto>> getAllTransactions(@RequestHeader("X-Org-Id") UUID orgId) {
        List<TransactionDto> transactions = transactionService.getAllTransactions(orgId);
        return ResponseEntity.ok(transactions);
    }

    @GetMapping("/{id}")
    public ResponseEntity<TransactionDto> getTransaction(@PathVariable UUID id,
                                                         @RequestHeader("X-Org-Id") UUID orgId) {
        TransactionDto transaction = transactionService.getTransactionById(id, orgId);
        return ResponseEntity.ok(transaction);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteTransaction(@PathVariable UUID id,
                                                  @RequestHeader("X-Org-Id") UUID orgId) {
        transactionService.deleteTransaction(id, orgId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/client/{clientId}")
    public ResponseEntity<List<TransactionDto>> getTransactionsByClient(@PathVariable UUID clientId,
                                                                        @RequestHeader("X-Org-Id") UUID orgId) {
        List<TransactionDto> transactions = transactionService.getTransactionsByClient(clientId, orgId);
        return ResponseEntity.ok(transactions);
    }

    @GetMapping("/range")
    public ResponseEntity<List<TransactionDto>> getTransactionsByDateRange(
            @RequestHeader("X-Org-Id") UUID orgId,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {
        List<TransactionDto> transactions = transactionService.getTransactionsByDateRange(orgId, startDate, endDate);
        return ResponseEntity.ok(transactions);
    }

    @GetMapping("/summary")
    public ResponseEntity<Map<String, BigDecimal>> getFinancialSummary(@RequestHeader("X-Org-Id") UUID orgId) {
        Map<String, BigDecimal> summary = transactionService.getFinancialSummary(orgId);
        return ResponseEntity.ok(summary);
    }
}