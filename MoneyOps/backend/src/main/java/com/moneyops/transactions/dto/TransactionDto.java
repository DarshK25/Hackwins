// src/main/java/com/moneyops/transactions/dto/TransactionDto.java
package com.moneyops.transactions.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

@Data
public class TransactionDto {
    private UUID id;
    private UUID clientId;
    private UUID invoiceId;
    private String type;
    private BigDecimal amount;
    private String currency;
    private LocalDate transactionDate;
    private String category;
    private String description;
    private String paymentMethod;
    private String referenceNumber;
    private String aiCategory;
    private Float aiConfidence;
}