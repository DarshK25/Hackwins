package com.moneyops.settings.dto;

import lombok.Data;
import java.time.LocalDate;
import java.util.List;

@Data
public class BusinessSettingsDto {
    private String id;
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
    private String primaryActivity;
    private String targetMarket;
    private List<String> keyProducts;
    private List<String> currentChallenges;
    private String accountingMethod;
    private String financialYearStartMonth;
    private String preferredLanguage;
    private String currency;
}
