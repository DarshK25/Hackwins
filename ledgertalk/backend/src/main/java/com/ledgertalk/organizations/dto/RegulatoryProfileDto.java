// src/main/java/com/ledgertalk/organizations/dto/RegulatoryProfileDto.java
package com.ledgertalk.organizations.dto;

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