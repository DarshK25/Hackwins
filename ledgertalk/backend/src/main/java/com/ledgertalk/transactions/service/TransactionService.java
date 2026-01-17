// src/main/java/com/ledgertalk/transactions/service/TransactionService.java
package com.ledgertalk.transactions.service;

import com.ledgertalk.transactions.dto.TransactionDto;
import com.ledgertalk.transactions.entity.Transaction;
import com.ledgertalk.transactions.entity.TransactionType;
import com.ledgertalk.transactions.mapper.TransactionMapper;
import com.ledgertalk.transactions.repository.TransactionRepository;
import com.ledgertalk.transactions.validator.TransactionValidator;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

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

    public List<TransactionDto> getAllTransactions(UUID orgId) {
        return transactionRepository.findAllByOrgId(orgId).stream()
                .map(transactionMapper::toDto)
                .collect(Collectors.toList());
    }

    public TransactionDto getTransactionById(UUID id, UUID orgId) {
        Transaction transaction = transactionRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new RuntimeException("Transaction not found"));
        return transactionMapper.toDto(transaction);
    }

    public TransactionDto createTransaction(TransactionDto dto, UUID orgId, UUID userId) {
        transactionValidator.validate(dto);

        Transaction transaction = transactionMapper.toEntity(dto);
        transaction.setOrgId(orgId);
        transaction.setCreatedBy(userId);
        transaction.setCreatedAt(LocalDateTime.now());
        transaction.setUpdatedAt(LocalDateTime.now());

        Transaction saved = transactionRepository.save(transaction);
        return transactionMapper.toDto(saved);
    }

    public TransactionDto updateTransaction(UUID id, TransactionDto dto, UUID orgId) {
        Transaction existing = transactionRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new RuntimeException("Transaction not found"));

        transactionValidator.validate(dto);

        Transaction updated = transactionMapper.toEntity(dto);
        updated.setId(id);
        updated.setOrgId(orgId);
        updated.setCreatedAt(existing.getCreatedAt());
        updated.setCreatedBy(existing.getCreatedBy());
        updated.setUpdatedAt(LocalDateTime.now());

        Transaction saved = transactionRepository.save(updated);
        return transactionMapper.toDto(saved);
    }

    public void deleteTransaction(UUID id, UUID orgId) {
        transactionRepository.deleteByIdAndOrgId(id, orgId);
    }

    public List<TransactionDto> getTransactionsByClient(UUID clientId, UUID orgId) {
        return transactionRepository.findByOrgIdAndClientId(orgId, clientId).stream()
                .map(transactionMapper::toDto)
                .collect(Collectors.toList());
    }

    public List<TransactionDto> getTransactionsByDateRange(UUID orgId, LocalDate startDate, LocalDate endDate) {
        return transactionRepository.findByOrgIdAndDateRange(orgId, startDate, endDate).stream()
                .map(transactionMapper::toDto)
                .collect(Collectors.toList());
    }

    public BigDecimal getTotalIncome(UUID orgId) {
        BigDecimal total = transactionRepository.getTotalByOrgIdAndType(orgId, TransactionType.INCOME);
        return total != null ? total : BigDecimal.ZERO;
    }

    public BigDecimal getTotalExpense(UUID orgId) {
        BigDecimal total = transactionRepository.getTotalByOrgIdAndType(orgId, TransactionType.EXPENSE);
        return total != null ? total : BigDecimal.ZERO;
    }

    public Map<String, BigDecimal> getFinancialSummary(UUID orgId) {
        BigDecimal income = getTotalIncome(orgId);
        BigDecimal expense = getTotalExpense(orgId);
        return Map.of(
            "totalIncome", income,
            "totalExpense", expense,
            "netProfit", income.subtract(expense)
        );
    }
}