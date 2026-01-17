// src/main/java/com/ledgertalk/organizations/entity/RegulatoryProfile.java
package com.ledgertalk.organizations.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.util.UUID;

@Entity
@Table(name = "regulatory_profiles")
@Data
public class RegulatoryProfile {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @OneToOne
    @JoinColumn(name = "org_id", nullable = false, unique = true)
    private BusinessOrganization organization;

    private String panNumber;

    private String stateOfRegistration;

    private Boolean gstRegistered;

    private String gstNumber;

    private String tanNumber;

    private String cinOrLlpIn;

    private String msmeNumber;

    private String iecCode;
}