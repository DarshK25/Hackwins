// src/main/java/com/ledgertalk/transactions/validator/TransactionValidator.java
package com.ledgertalk.transactions.validator;

import com.ledgertalk.transactions.dto.TransactionDto;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

@Component
public class TransactionValidator {

    public void validate(TransactionDto dto) {
        if (dto.getType() == null || dto.getType().isEmpty()) {
            throw new IllegalArgumentException("Transaction type is required");
        }
        if (!"INCOME".equals(dto.getType()) && !"EXPENSE".equals(dto.getType())) {
            throw new IllegalArgumentException("Transaction type must be INCOME or EXPENSE");
        }
        if (dto.getAmount() == null || dto.getAmount().compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Amount must be positive");
        }
        if (dto.getTransactionDate() == null) {
            throw new IllegalArgumentException("Transaction date is required");
        }
        if (dto.getCategory() == null || dto.getCategory().isEmpty()) {
            throw new IllegalArgumentException("Category is required");
        }
    }
}