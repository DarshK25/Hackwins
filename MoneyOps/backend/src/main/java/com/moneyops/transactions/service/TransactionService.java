// src/main/java/com/moneyops/transactions/service/TransactionService.java
package com.moneyops.transactions.service;

import com.moneyops.transactions.dto.TransactionDto;
import com.moneyops.transactions.entity.Transaction;
import com.moneyops.transactions.entity.TransactionType;
import com.moneyops.transactions.mapper.TransactionMapper;
import com.moneyops.transactions.repository.TransactionRepository;
import com.moneyops.transactions.validator.TransactionValidator;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional
public class TransactionService {

    private final TransactionRepository transactionRepository;
    private final TransactionMapper transactionMapper;
    private final TransactionValidator transactionValidator;

    public List<TransactionDto> getAllTransactions(String orgId) {
        if (orgId == null || orgId.isBlank()) throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing organization context");
        return transactionRepository.findAllByOrgIdAndDeletedAtIsNull(orgId).stream()
                .map(transactionMapper::toDto)
                .collect(Collectors.toList());
    }

    public TransactionDto getTransactionById(String id, String orgId) {
        Transaction transaction = transactionRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Transaction not found"));
        return transactionMapper.toDto(transaction);
    }

    public TransactionDto createTransaction(TransactionDto dto, String orgId, String userId) {
        if (orgId == null || orgId.isBlank()) throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing organization context");
        
        // ✨ Idempotency check
        if (dto.getIdempotencyKey() != null) {
            // Note: In a production app, we'd query an idempotency_keys collection
            // but for now we'll check if a transaction with this key exists
            var existing = transactionRepository.findAllByOrgIdAndDeletedAtIsNull(orgId).stream()
                .filter(t -> dto.getIdempotencyKey().equals(t.getIdempotencyKey()))
                .findFirst();
            if (existing.isPresent()) return transactionMapper.toDto(existing.get());
        }

        transactionValidator.validate(dto);

        Transaction transaction = transactionMapper.toEntity(dto);
        transaction.setOrgId(orgId);
        
        if (transaction.getTransactionDate() == null) {
            transaction.setTransactionDate(LocalDate.now());
        }
        if (transaction.getCurrency() == null) {
            transaction.setCurrency("INR");
        }

        Transaction saved = transactionRepository.save(transaction);
        return transactionMapper.toDto(saved);
    }

    public TransactionDto updateTransaction(String id, TransactionDto dto, String orgId) {
        Transaction existing = transactionRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Transaction not found"));

        transactionValidator.validate(dto);

        existing.setClientId(dto.getClientId());
        existing.setInvoiceId(dto.getInvoiceId());
        existing.setType(TransactionType.valueOf(dto.getType().toUpperCase()));
        existing.setAmount(dto.getAmount());
        existing.setCurrency(dto.getCurrency() != null ? dto.getCurrency() : "INR");
        existing.setTransactionDate(dto.getTransactionDate());
        existing.setCategory(dto.getCategory());
        existing.setDescription(dto.getDescription());
        existing.setPaymentMethod(dto.getPaymentMethod());
        existing.setReferenceNumber(dto.getReferenceNumber());

        Transaction saved = transactionRepository.save(existing);
        return transactionMapper.toDto(saved);
    }

    public void deleteTransaction(String id, String orgId) {
        Transaction transaction = transactionRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Transaction not found"));
        
        // ✨ Soft Delete
        transaction.setDeletedAt(LocalDateTime.now());
        transactionRepository.save(transaction);
    }

    public List<TransactionDto> getTransactionsByClient(String clientId, String orgId) {
        return transactionRepository.findByOrgIdAndClientIdAndDeletedAtIsNull(orgId, clientId).stream()
                .map(transactionMapper::toDto)
                .collect(Collectors.toList());
    }

    public List<TransactionDto> getTransactionsByInvoice(String invoiceId, String orgId) {
        return transactionRepository.findByOrgIdAndInvoiceIdAndDeletedAtIsNull(orgId, invoiceId).stream()
                .map(transactionMapper::toDto)
                .collect(Collectors.toList());
    }

    public List<TransactionDto> getTransactionsByDateRange(String orgId, LocalDate startDate, LocalDate endDate) {
        return transactionRepository.findByOrgIdAndTransactionDateBetweenAndDeletedAtIsNull(orgId, startDate, endDate).stream()
                .map(transactionMapper::toDto)
                .collect(Collectors.toList());
    }

    public BigDecimal getTotalIncome(String orgId) {
        var result = transactionRepository.getTotalByOrgIdAndType(orgId, TransactionType.INCOME);
        return (result != null && result.total() != null) ? BigDecimal.valueOf(result.total()) : BigDecimal.ZERO;
    }

    public BigDecimal getTotalExpense(String orgId) {
        var result = transactionRepository.getTotalByOrgIdAndType(orgId, TransactionType.EXPENSE);
        return (result != null && result.total() != null) ? BigDecimal.valueOf(result.total()) : BigDecimal.ZERO;
    }

    public Map<String, BigDecimal> getFinancialSummary(String orgId) {
        BigDecimal income = getTotalIncome(orgId);
        BigDecimal expense = getTotalExpense(orgId);
        return Map.of(
            "totalIncome", income,
            "totalExpense", expense,
            "netProfit", income.subtract(expense)
        );
    }
}