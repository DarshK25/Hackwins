package com.moneyops.transactions.entity;

import jakarta.annotation.PostConstruct;
import lombok.Data;
import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.Id;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.CompoundIndex;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

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
    private String orgId;

    @Indexed
    private String clientId;

    @Indexed
    private String invoiceId;

    private TransactionType type;
    private BigDecimal amount;
    private String currency = "INR";
    private LocalDate transactionDate;
    private String category;
    private String description;
    private String paymentMethod;
    private String receiptUrl;
    private String referenceNumber;
    private String status = "COMPLETED";
    private String aiCategory;
    private Float aiConfidence;
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
