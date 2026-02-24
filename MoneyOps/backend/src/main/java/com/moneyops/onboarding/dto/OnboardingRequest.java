package com.moneyops.onboarding.dto;

import lombok.Data;
import java.util.List;

/**
 * Request body for:
 *   POST /api/onboarding/create-business
 *   POST /api/onboarding/join-business
 *
 * Field names match exactly what the frontend sends.
 */
@Data
public class OnboardingRequest {

    // Always present (added by frontend from Clerk session)
    private String clerkId;   // Clerk user ID e.g. "user_2abc123xyz"
    private String email;     // user's email from Clerk
    private String name;      // user's personal name from Clerk (not the business name)

    // ── Step 1: BusinessInfoStep ───────────────────────────────────────────────
    private String legalName;           // company legal name (renamed from "name" by frontend)
    private String tradingName;
    private String businessType;        // "sole_proprietorship" | "partnership" | "llp" | "private_limited" | "public_limited" | "opc"
    private String industry;            // "it_software" | "manufacturing" | "retail" | "services" | "healthcare" | "education" | "construction" | "hospitality" | "finance" | "other"
    private String registrationDate;    // "2020-04-01"
    private String annualTurnover;      // "below_10l" | "10l_to_1cr" | "1cr_to_10cr" | "above_10cr"
    private String primaryEmail;
    private String primaryPhone;
    private String website;
    private Integer numberOfEmployees;
    private String registeredAddress;

    // ── Step 2: RegulatoryInfoStep ─────────────────────────────────────────────
    private String panNumber;                 // PAN number
    private String stateOfRegistration;
    private Boolean gstRegistered;
    private String gstin;
    private String gstFilingFrequency;  // "monthly" | "quarterly"
    private String tanNumber;                 // TAN number
    private String cin;                 // CIN or LLPIN
    private String llpin;
    private String msmeNumber;
    private String iecCode;
    private String professionalTaxReg;

    // ── Step 3: BusinessContextStep ────────────────────────────────────────────
    private String primaryActivity;
    private String targetMarket;        // "B2B" | "B2C" | "B2G"
    private List<String> keyProducts;
    private List<String> currentChallenges;
    private String accountingMethod;    // "accrual" | "cash"
    private Integer fyStartMonth;       // 1–12, default 4 (April)
    private String preferredLanguage;   // "en" | "hi" | "mr" etc.

    // ── join-business only ─────────────────────────────────────────────────────
    private String inviteCode;
}
