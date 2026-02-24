package com.moneyops.clients.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;
import org.springframework.data.mongodb.core.mapping.MongoId;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "clients")
@Data
public class Client {

    /**
     * Use String as the @Id type to avoid "Cannot autogenerate id of type UUID"
     * from Spring Data MongoDB. We generate a UUID ourselves and store it as a
     * string — this gives us stable UUID string IDs that map cleanly to Java UUIDs
     * via the DTO layer.
     */
    @Id
    private String id = UUID.randomUUID().toString();

    private UUID orgId;
    private String name;
    private String taxId;       // Client's GST/PAN
    private String email;
    private String phoneNumber;
    private String address;
    private String city;
    private String state;
    private String country;
    private String postalCode;
    private String paymentTerms; // e.g. "Net 30"
    private String currency = "INR";
    private String company;
    private String notes;
    private Status status = Status.ACTIVE;

    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();
    private UUID createdBy;
    private UUID updatedBy;

    public enum Status {
        ACTIVE, INACTIVE, SUSPENDED
    }
}