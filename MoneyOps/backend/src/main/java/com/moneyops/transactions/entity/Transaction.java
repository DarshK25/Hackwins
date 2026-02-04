// src/main/java/com/moneyops/transactions/entity/Transaction.java
package com.moneyops.transactions.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "transactions")
@Data
public class Transaction {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private UUID orgId;

    private UUID clientId; // null if expense

    private UUID invoiceId; // null if not related to invoice

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private TransactionType type; // INCOME or EXPENSE

    @Column(nullable = false, precision = 19, scale = 2)
    private BigDecimal amount;

    @Column(nullable = false)
    private String currency = "INR";

    @Column(nullable = false)
    private LocalDate transactionDate;

    @Column(nullable = false)
    private String category; // e.g., "Payment Received", "Office Rent", "Salary"

    @Column(columnDefinition = "TEXT")
    private String description;

    private String paymentMethod; // e.g., "Bank Transfer", "Cash", "UPI"

    private String referenceNumber; // Transaction ID, Check number, etc.

    // AI classification
    private String aiCategory; // AI suggested category
    private Float aiConfidence; // 0.0 to 1.0

    @Column(nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(nullable = false)
    private LocalDateTime updatedAt = LocalDateTime.now();

    @Column(nullable = false)
    private UUID createdBy;
}