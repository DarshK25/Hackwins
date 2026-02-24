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
@Document(collection = "business_organizations")
@Data
public class BusinessOrganization {

    @Id
    private UUID id = UUID.randomUUID();

    // ── Step 1: Business Info ──────────────────────────────────────────────────
    private String legalName;           // company's legal name
    private String tradingName;         // brand/trading name (optional)

    /** e.g. "sole_proprietorship" | "partnership" | "llp" | "private_limited" | "public_limited" | "opc" */
    private String businessType;

    /** e.g. "it_software" | "manufacturing" | "retail" | "services" | "healthcare" | "education" | "construction" | "hospitality" | "finance" | "other" */
    private String industry;

    private LocalDate registrationDate;    // ISO date string e.g. "2020-04-01"

    /** e.g. "below_10l" | "10l_to_1cr" | "1cr_to_10cr" | "above_10cr" */
    private String annualTurnover;

    private String primaryEmail;
    private String primaryPhone;
    private String website;
    private Integer employeeCount;
    private String registeredAddress;

    // ── Step 2: Regulatory Info ────────────────────────────────────────────────
    private String panNumber;
    private String stateOfRegistration;
    private Boolean gstRegistered;
    private String gstin;

    /** "monthly" | "quarterly" */
    private String gstFilingFrequency;

    private String tanNumber;
    private String cin;
    private String llpin;
    private String msmeNumber;
    private String iecCode;
    private String professionalTaxReg;

    // ── Step 3: Business Context ───────────────────────────────────────────────
    private String primaryActivity;

    /** "B2B" | "B2C" | "B2G" */
    private String targetMarket;

    private List<String> keyProducts;           // up to 5
    private List<String> currentChallenges;     // multi-select

    /** "accrual" | "cash" */
    private String accountingMethod;

    private Integer fyStartMonth;       // 1–12 (default 4 = April)

    /** "en" | "hi" | "mr" etc. */
    private String preferredLanguage;

    // ── Audit ──────────────────────────────────────────────────────────────────
    private UUID createdBy;
    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();
}