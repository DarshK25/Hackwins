// src/main/java/com/moneyops/organizations/dto/BusinessOrganizationDto.java
package com.moneyops.organizations.dto;

import lombok.Data;
import java.time.LocalDate;
import java.util.List;

@Data
public class BusinessOrganizationDto {
    private String id;
    private Boolean teamSecurityCodeConfigured;
    private String legalName;
    private String tradingName;
    private String businessType;
    private String industry;
    private LocalDate registrationDate;
    private String annualTurnoverRange;
    private String primaryEmail;
    private String primaryPhone;
    private String website;
    private Integer employeeCount;
    private String registeredAddress;
    private String pincode;
    private String financialYearStartMonth;
    private String preferredLanguage;
    private String primaryActivity;
    private String targetMarket;
    private String accountingMethod;
    private List<String> keyProducts;
    private List<String> currentChallenges;

    // Regulatory fields
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

    private String verificationTier;
}
