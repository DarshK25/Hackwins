package com.moneyops.organizations.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDate;
import java.time.LocalDateTime;

import java.util.List;
import java.util.UUID;

/**
 * MongoDB collection: "business_organizations"
 *
 * All fields are stored as plain strings so they match exactly
 * what the frontend form sends — no enum conversion needed.
 */
import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.mapping.Document;
import jakarta.annotation.PostConstruct;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Document(collection = "business_organizations")
@Data
public class BusinessOrganization {

    @Id
    private String id;

    // ── Step 1: Business Info ──────────────────────────────────────────────────
    private String legalName;
    private String tradingName;
    private String businessType;
    private String industry;
    private LocalDate registrationDate;
    private String annualTurnover;
    private String primaryEmail;
    private String primaryPhone;
    private String website;
    private Integer employeeCount;
    private String registeredAddress;
    private String pincode;

    // ── Step 2: Regulatory Info ────────────────────────────────────────────────
    private String panNumber;
    private String stateOfRegistration;
    private Boolean gstRegistered;
    private String gstin;
    private String gstFilingFrequency;
    private String tanNumber;
    private String cin;
    private String llpin;
    private String msmeNumber;
    private String iecCode;
    private String professionalTaxReg;

    // ── Step 3: Business Context ───────────────────────────────────────────────
    private String primaryActivity;
    private String targetMarket;
    private List<String> keyProducts;
    private List<String> currentChallenges;
    private String accountingMethod;
    private Integer fyStartMonth;
    private String preferredLanguage;

    // ── Audit ──────────────────────────────────────────────────────────────────
    @CreatedDate
    private LocalDateTime createdAt;
    
    @LastModifiedDate
    private LocalDateTime updatedAt;
    
    @CreatedBy
    private String createdBy;
    
    @LastModifiedBy
    private String updatedBy;
    
    private LocalDateTime deletedAt;

    @PostConstruct
    public void generateId() {
        if (this.id == null) {
            this.id = UUID.randomUUID().toString();
        }
    }
}