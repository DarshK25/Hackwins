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

    public List<TransactionDto> getAllTransactions(UUID orgId) {
        return transactionRepository.findAllByOrgId(orgId).stream()
                .map(transactionMapper::toDto)
                .collect(Collectors.toList());
    }

    public TransactionDto getTransactionById(UUID id, UUID orgId) {
        Transaction transaction = transactionRepository.findByIdAndOrgId(id, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Transaction not found"));
        return transactionMapper.toDto(transaction);
    }

    public TransactionDto createTransaction(TransactionDto dto, UUID orgId, UUID userId) {
        transactionValidator.validate(dto);

        Transaction transaction = new Transaction();

        transaction.setOrgId(orgId);
        transaction.setCreatedBy(userId);
        transaction.setCreatedAt(LocalDateTime.now());
        transaction.setUpdatedAt(LocalDateTime.now());

        transaction.setClientId(dto.getClientId());
        transaction.setInvoiceId(dto.getInvoiceId());

        transaction.setType(TransactionType.valueOf(dto.getType().toUpperCase()));

        transaction.setAmount(dto.getAmount());
        transaction.setCurrency(dto.getCurrency() != null ? dto.getCurrency() : "INR");

        transaction.setTransactionDate(
                dto.getTransactionDate() != null ? dto.getTransactionDate() : LocalDate.now()
        );

        transaction.setCategory(dto.getCategory());
        transaction.setDescription(dto.getDescription());
        transaction.setPaymentMethod(dto.getPaymentMethod());
        transaction.setReferenceNumber(dto.getReferenceNumber());

        Transaction saved = transactionRepository.save(transaction);
        return transactionMapper.toDto(saved);
    }

    public TransactionDto updateTransaction(UUID id, TransactionDto dto, UUID orgId) {
        Transaction existing = transactionRepository.findByIdAndOrgId(id, orgId)
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

        existing.setUpdatedAt(LocalDateTime.now());

        Transaction saved = transactionRepository.save(existing);
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

    public List<TransactionDto> getTransactionsByInvoice(String invoiceId, UUID orgId) {
        return transactionRepository.findByOrgIdAndInvoiceId(orgId, invoiceId).stream()
                .map(transactionMapper::toDto)
                .collect(Collectors.toList());
    }

    public List<TransactionDto> getTransactionsByDateRange(UUID orgId, LocalDate startDate, LocalDate endDate) {
        return transactionRepository.findByOrgIdAndTransactionDateBetween(orgId, startDate, endDate).stream()
                .map(transactionMapper::toDto)
                .collect(Collectors.toList());
    }

    public BigDecimal getTotalIncome(UUID orgId) {
        var result = transactionRepository.getTotalByOrgIdAndType(orgId, TransactionType.INCOME);
        return (result != null && result.total() != null) ? BigDecimal.valueOf(result.total()) : BigDecimal.ZERO;
    }

    public BigDecimal getTotalExpense(UUID orgId) {
        var result = transactionRepository.getTotalByOrgIdAndType(orgId, TransactionType.EXPENSE);
        return (result != null && result.total() != null) ? BigDecimal.valueOf(result.total()) : BigDecimal.ZERO;
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