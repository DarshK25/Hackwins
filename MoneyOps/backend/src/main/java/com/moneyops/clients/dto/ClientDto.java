// src/main/java/com/moneyops/clients/dto/ClientDto.java
package com.moneyops.clients.dto;

import lombok.Data;
import java.time.LocalDateTime;
import java.util.UUID;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class ClientDto {
    private String id;
    private String orgId;      // ✨ New per schema
    private String name;
    private String gstin;      // WAS taxId
    private String email;
    private String phoneNumber;

    /**
     * Raw team security code (PIN) required for protected create actions.
     * It is verified by the backend against a BCrypt hash stored in the org.
     */
    private String teamActionCode;

    /**
     * Source of the create action: MANUAL / AI / VOICE.
     */
    private String source;
    
    // ✨ Expanded address per schema
    private Address billingAddress;
    private Address shippingAddress;
    
    private Integer paymentTerms; // WAS String, NOW Integer (Days)
    private String currency;
    private String company;
    private String notes;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private String createdBy;
    private String createdByEmail;
    private String createdByRole;
    private String updatedBy;
    private Double searchScore;
    private String idempotencyKey; // ✨ New

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