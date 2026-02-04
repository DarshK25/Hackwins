// src/main/java/com/moneyops/organizations/dto/BusinessOrganizationDto.java
package com.moneyops.organizations.dto;

import lombok.Data;
import java.time.LocalDate;
import java.util.UUID;

@Data
public class BusinessOrganizationDto {
    private UUID id;
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
    private String financialYearStartMonth;
    private String preferredLanguage;
    private String primaryActivity;
    private String targetMarket;
    private String accountingMethod;
}