package com.moneyops.organizations.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.util.UUID;

@Document(collection = "regulatory_profiles")
@Data
public class RegulatoryProfile {

    @Id
    private UUID id = UUID.randomUUID();

    private UUID orgId; // references BusinessOrganization._id

    private String panNumber;
    private String stateOfRegistration;
    private Boolean gstRegistered;
    private String gstNumber;
    private String tanNumber;
    private String cinOrLlpIn;
    private String msmeNumber;
    private String iecCode;
}