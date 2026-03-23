package com.moneyops.invoices.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import jakarta.annotation.PostConstruct;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Document(collection = "invoices")
@Data
public class Invoice {

    @Id
    private String id;

    @Indexed
    private String orgId;      // 🔗 Tenant isolation
    
    @Indexed
    private String invoiceNumber; // Unique per org
    
    @Indexed
    private String clientId;   // 🔗 WAS UUID, NOW String
    
    private String clientName;
    private String clientEmail;
    private String clientCompany;
    private String clientPhone;
    
    private LocalDate issueDate;
    private LocalDate dueDate;
    private InvoiceStatus status = InvoiceStatus.DRAFT;
    
    private BigDecimal subtotal;
    private BigDecimal gstTotal;
    private BigDecimal totalAmount;
    private BigDecimal amountPaid = BigDecimal.ZERO;  // ✨ New
    private BigDecimal balanceDue;                     // ✨ New
    
    private String currency = "INR";
    private LocalDate paymentDate;
    private String notes;
    private String termsAndConditions; // ✨ New

    private List<InvoiceItem> items;

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
        private boolean createdViaVoice;
        private String transcript;
    }
}