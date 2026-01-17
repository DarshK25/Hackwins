// src/main/java/com/ledgertalk/transactions/mapper/TransactionMapper.java
package com.ledgertalk.transactions.mapper;

import com.ledgertalk.transactions.dto.TransactionDto;
import com.ledgertalk.transactions.entity.Transaction;
import com.ledgertalk.transactions.entity.TransactionType;
import org.springframework.stereotype.Component;

@Component
public class TransactionMapper {

    public TransactionDto toDto(Transaction transaction) {
        TransactionDto dto = new TransactionDto();
        dto.setId(transaction.getId());
        dto.setClientId(transaction.getClientId());
        dto.setInvoiceId(transaction.getInvoiceId());
        dto.setType(transaction.getType().name());
        dto.setAmount(transaction.getAmount());
        dto.setCurrency(transaction.getCurrency());
        dto.setTransactionDate(transaction.getTransactionDate());
        dto.setCategory(transaction.getCategory());
        dto.setDescription(transaction.getDescription());
        dto.setPaymentMethod(transaction.getPaymentMethod());
        dto.setReferenceNumber(transaction.getReferenceNumber());
        dto.setAiCategory(transaction.getAiCategory());
        dto.setAiConfidence(transaction.getAiConfidence());
        return dto;
    }

    public Transaction toEntity(TransactionDto dto) {
        Transaction transaction = new Transaction();
        transaction.setId(dto.getId());
        transaction.setClientId(dto.getClientId());
        transaction.setInvoiceId(dto.getInvoiceId());
        transaction.setType(TransactionType.valueOf(dto.getType()));
        transaction.setAmount(dto.getAmount());
        transaction.setCurrency(dto.getCurrency());
        transaction.setTransactionDate(dto.getTransactionDate());
        transaction.setCategory(dto.getCategory());
        transaction.setDescription(dto.getDescription());
        transaction.setPaymentMethod(dto.getPaymentMethod());
        transaction.setReferenceNumber(dto.getReferenceNumber());
        transaction.setAiCategory(dto.getAiCategory());
        transaction.setAiConfidence(dto.getAiConfidence());
        return transaction;
    }
}