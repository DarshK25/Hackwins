// src/main/java/com/moneyops/transactions/dto/TransactionDto.java
package com.moneyops.transactions.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;


@Data
public class TransactionDto {
    private String id;
    private String orgId;
    private String clientId;
    private String invoiceId;
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
    private String idempotencyKey;
    private com.moneyops.transactions.entity.Transaction.VoiceContext voiceContext;
}