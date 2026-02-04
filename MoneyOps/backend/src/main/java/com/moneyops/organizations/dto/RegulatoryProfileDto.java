// src/main/java/com/moneyops/organizations/dto/RegulatoryProfileDto.java
package com.moneyops.organizations.dto;

import lombok.Data;

@Data
public class RegulatoryProfileDto {
    private String panNumber;
    private String stateOfRegistration;
    private Boolean gstRegistered;
    private String gstNumber;
    private String tanNumber;
    private String cinOrLlpIn;
    private String msmeNumber;
    private String iecCode;
}