// src/main/java/com/moneyops/transactions/validator/TransactionValidator.java
package com.moneyops.transactions.validator;

import com.moneyops.transactions.dto.TransactionDto;
import com.moneyops.transactions.entity.TransactionType;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

@Component
public class TransactionValidator {

    public void validate(TransactionDto dto) {

        if (dto.getAmount() == null || dto.getAmount().compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("Amount must be greater than zero");
        }

        if (dto.getType() == null) {
            throw new IllegalArgumentException("Transaction type is required");
        }

        try {
            TransactionType.valueOf(dto.getType().toUpperCase());
        } catch (Exception e) {
            throw new IllegalArgumentException("Invalid transaction type");
        }

        if (dto.getTransactionDate() == null) {
            throw new IllegalArgumentException("Transaction date is required");
        }
    }
}