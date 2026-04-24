package com.moneyops.expenses.dto;

import com.moneyops.transactions.entity.Transaction;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
public class ExpenseDTO {
    private String id;
    private String orgId;
    private BigDecimal amount;
    private String category;
    private String description;
    private LocalDate date;
    private String paymentMethod;
    private String receiptUrl;
    private String teamActionCode;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private Transaction.VoiceContext voiceContext;
}
