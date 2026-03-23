package com.moneyops.clients.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;
import org.springframework.data.mongodb.core.mapping.MongoId;

import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import jakarta.annotation.PostConstruct;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "clients")
@Data
public class Client {

    @Id
    private String id;

    @Indexed
    private String orgId;      // 🔗 Tenant isolation (String ID)
    private String name;
    private String gstin;      // ✨ WAS taxId, NOW gstin as per schema
    private String email;
    private String phoneNumber;
    
    // ✨ Schema-v2: Expanded address structure
    private Address billingAddress;
    private Address shippingAddress;
    
    private Integer paymentTerms; // WAS String, NOW Integer (Days) as per schema
    private String currency = "INR";
    private String company;
    private String notes;
    private Status status = Status.ACTIVE;

    // ✨ Audit Fields (Auto-populated by @EnableMongoAuditing)
    @CreatedDate
    private LocalDateTime createdAt;
    
    @LastModifiedDate
    private LocalDateTime updatedAt;
    
    @CreatedBy
    private String createdBy;  // Clerk userId (String)
    
    @LastModifiedBy
    private String updatedBy;
    
    private LocalDateTime deletedAt; // ✨ Soft delete support
    
    @Indexed(unique = true, partialFilter = "{'idempotencyKey': {$exists: true}}")
    private String idempotencyKey; // ✨ From AI Gateway

    @PostConstruct
    public void generateId() {
        if (this.id == null) {
            this.id = UUID.randomUUID().toString();
        }
    }

    public enum Status {
        ACTIVE, INACTIVE, SUSPENDED
    }

    @Data
    public static class Address {
        private String line1;
        private String line2;
        private String city;
        private String state;
        private String country;
        private String pincode;
    }
}