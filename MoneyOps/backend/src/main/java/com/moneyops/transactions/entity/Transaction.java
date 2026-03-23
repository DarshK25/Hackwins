package com.moneyops.transactions.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.mapping.Document;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import jakarta.annotation.PostConstruct;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "transactions")
@CompoundIndex(name = "org_type_idx", def = "{'orgId': 1, 'type': 1, 'deletedAt': 1}")
@Data
public class Transaction {

    @Id
    private String id;

    @Indexed
    private String orgId;      // 🔗 Tenant isolation
    
    @Indexed
    private String clientId;   // 🔗 WAS UUID, NOW String
    
    @Indexed
    private String invoiceId;  // 🔗 Ref to invoices (String)
    
    private TransactionType type;
    private BigDecimal amount;
    private String currency = "INR";
    private LocalDate transactionDate;
    private String category;
    private String description;
    private String paymentMethod;
    private String referenceNumber;

    // AI classification
    private String aiCategory;
    private Float aiConfidence;

    // ✨ Voice Context Metadata
    private VoiceContext voiceContext;

    @CreatedDate
    private LocalDateTime createdAt;
    
    @LastModifiedDate
    private LocalDateTime updatedAt;
    
    @CreatedBy
    private String createdBy;
    
    @LastModifiedBy
    private String updatedBy;
    
    private LocalDateTime deletedAt;

    @Indexed(unique = true, partialFilter = "{'idempotencyKey': {$exists: true}}")
    private String idempotencyKey;

    @PostConstruct
    public void generateId() {
        if (this.id == null) {
            this.id = UUID.randomUUID().toString();
        }
    }

    @Data
    public static class VoiceContext {
        private String sessionId;
        private boolean recordedViaVoice;
        private String transcript;
    }
}