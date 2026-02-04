// src/main/java/com/moneyops/clients/entity/Client.java
package com.moneyops.clients.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "clients")
@Data
public class Client {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private UUID orgId;

    @Column(nullable = false)
    private String name;

    private String taxId; // Client's GST/PAN

    @Column(nullable = false)
    private String email;

    private String phoneNumber;

    private String address;
    private String city;
    private String state;
    private String country;
    private String postalCode;

    // Financial info
    private String paymentTerms; // e.g., "Net 30", "Net 60"
    private String currency = "INR";

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Status status = Status.ACTIVE;

    @Column(nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(nullable = false)
    private LocalDateTime updatedAt = LocalDateTime.now();

    @Column(nullable = false)
    private UUID createdBy;

    private UUID updatedBy;

    public enum Status {
        ACTIVE, INACTIVE, SUSPENDED
    }
}