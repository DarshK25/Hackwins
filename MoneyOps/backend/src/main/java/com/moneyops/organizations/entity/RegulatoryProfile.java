package com.moneyops.organizations.entity;

import jakarta.annotation.PostConstruct;
import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "regulatory_profiles")
@Data
public class RegulatoryProfile {

    @Id
    private String id;

    @Indexed
    private String orgId; // 🔗 Tenant isolation

    private String panNumber;
    private String stateOfRegistration;
    private Boolean gstRegistered;
    private String gstNumber;
    private String tanNumber;
    private String cinOrLlpIn;
    private String msmeNumber;
    private String iecCode;

    private LocalDateTime deletedAt; // ✨ Soft delete support

    @PostConstruct
    public void generateId() {
        if (this.id == null) {
            this.id = UUID.randomUUID().toString();
        }
    }
}