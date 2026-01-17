// src/main/java/com/ledgertalk/clients/dto/ClientDto.java
package com.ledgertalk.clients.dto;

import lombok.Data;
import java.time.LocalDateTime;
import java.util.UUID;

@Data
public class ClientDto {
    private UUID id;
    private String name;
    private String taxId;
    private String email;
    private String phoneNumber;
    private String address;
    private String city;
    private String state;
    private String country;
    private String postalCode;
    private String paymentTerms;
    private String currency;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private UUID createdBy;
    private UUID updatedBy;
}