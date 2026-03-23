// src/main/java/com/moneyops/transactions/controller/TransactionController.java
package com.moneyops.transactions.controller;

import com.moneyops.transactions.dto.TransactionDto;
import com.moneyops.transactions.service.TransactionService;
import com.moneyops.shared.utils.OrgContext;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/transactions")
@RequiredArgsConstructor
public class TransactionController {

    private final TransactionService transactionService;

    @PostMapping
    public ResponseEntity<TransactionDto> createTransaction(@RequestBody TransactionDto dto) {
        String orgId = OrgContext.getOrgId();
        String userId = OrgContext.getUserId();
        if (orgId == null) return ResponseEntity.status(org.springframework.http.HttpStatus.UNAUTHORIZED).build();

        TransactionDto created = transactionService.createTransaction(dto, orgId, userId);
        return ResponseEntity.ok(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<TransactionDto> updateTransaction(@PathVariable String id,
                                                            @RequestBody TransactionDto dto) {
        String orgId = OrgContext.getOrgId();
        if (orgId == null) return ResponseEntity.status(org.springframework.http.HttpStatus.UNAUTHORIZED).build();

        TransactionDto updated = transactionService.updateTransaction(id, dto, orgId);
        return ResponseEntity.ok(updated);
    }

    @GetMapping
    public ResponseEntity<List<TransactionDto>> getAllTransactions() {
        String orgId = OrgContext.getOrgId();
        if (orgId == null) return ResponseEntity.ok(List.of());

        List<TransactionDto> transactions = transactionService.getAllTransactions(orgId);
        return ResponseEntity.ok(transactions);
    }

    @GetMapping("/{id}")
    public ResponseEntity<TransactionDto> getTransaction(@PathVariable String id) {
        String orgId = OrgContext.getOrgId();
        if (orgId == null) return ResponseEntity.status(org.springframework.http.HttpStatus.UNAUTHORIZED).build();

        TransactionDto transaction = transactionService.getTransactionById(id, orgId);
        return ResponseEntity.ok(transaction);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteTransaction(@PathVariable String id) {
        String orgId = OrgContext.getOrgId();
        if (orgId == null) return ResponseEntity.status(org.springframework.http.HttpStatus.UNAUTHORIZED).build();

        transactionService.deleteTransaction(id, orgId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/client/{clientId}")
    public ResponseEntity<List<TransactionDto>> getTransactionsByClient(@PathVariable String clientId) {
        String orgId = OrgContext.getOrgId();
        if (orgId == null) return ResponseEntity.ok(List.of());

        List<TransactionDto> transactions = transactionService.getTransactionsByClient(clientId, orgId);
        return ResponseEntity.ok(transactions);
    }

    @GetMapping("/range")
    public ResponseEntity<List<TransactionDto>> getTransactionsByDateRange(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate startDate,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate endDate) {
        String orgId = OrgContext.getOrgId();
        if (orgId == null) return ResponseEntity.ok(List.of());

        List<TransactionDto> transactions = transactionService.getTransactionsByDateRange(orgId, startDate, endDate);
        return ResponseEntity.ok(transactions);
    }

    @GetMapping("/summary")
    public ResponseEntity<Map<String, BigDecimal>> getFinancialSummary() {
        String orgId = OrgContext.getOrgId();
        if (orgId == null) return ResponseEntity.status(org.springframework.http.HttpStatus.UNAUTHORIZED).build();

        Map<String, BigDecimal> summary = transactionService.getFinancialSummary(orgId);
        return ResponseEntity.ok(summary);
    }
}