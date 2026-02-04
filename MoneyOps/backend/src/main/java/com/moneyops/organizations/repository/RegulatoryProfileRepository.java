// src/main/java/com/moneyops/organizations/repository/RegulatoryProfileRepository.java
package com.moneyops.organizations.repository;

import com.moneyops.organizations.entity.RegulatoryProfile;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface RegulatoryProfileRepository extends JpaRepository<RegulatoryProfile, UUID> {

    Optional<RegulatoryProfile> findByOrganizationId(UUID orgId);
}