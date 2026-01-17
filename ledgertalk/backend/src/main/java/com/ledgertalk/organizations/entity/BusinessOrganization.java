// src/main/java/com/ledgertalk/organizations/entity/BusinessOrganization.java
package com.ledgertalk.organizations.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "business_organizations")
@Data
public class BusinessOrganization {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private String legalName;

    private String tradingName;

    @Enumerated(EnumType.STRING)
    private BusinessType businessType;

    @Enumerated(EnumType.STRING)
    private Industry industry;

    private LocalDate registrationDate;

    @Enumerated(EnumType.STRING)
    private TurnoverRange annualTurnoverRange;

    private String primaryEmail;

    private String primaryPhone;

    private String website;

    private Integer employeeCount;

    @Column(columnDefinition = "TEXT")
    private String registeredAddress;

    @Enumerated(EnumType.STRING)
    private Month financialYearStartMonth;

    private String preferredLanguage;

    private String primaryActivity;

    @Enumerated(EnumType.STRING)
    private TargetMarket targetMarket;

    @Enumerated(EnumType.STRING)
    private AccountingMethod accountingMethod;

    @Column(nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(nullable = false)
    private LocalDateTime updatedAt = LocalDateTime.now();

    @Column(nullable = false)
    private UUID createdBy;

    // Enums
    public enum BusinessType {
        Proprietorship, Partnership, LLP, PvtLtd, PublicLtd, NGO, Other
    }

    public enum Industry {
        IT, Manufacturing, Retail, Healthcare, Education, Finance, Hospitality, Construction, Other
    }

    public enum TurnoverRange {
        LESS_THAN_10L, TEN_TO_50L, FIFTY_TO_2CR, TWO_TO_10CR, MORE_THAN_10CR
    }

    public enum Month {
        JAN, FEB, MAR, APR, MAY, JUN, JUL, AUG, SEP, OCT, NOV, DEC
    }

    public enum TargetMarket {
        Local, National, International
    }

    public enum AccountingMethod {
        Cash, Accrual
    }
}