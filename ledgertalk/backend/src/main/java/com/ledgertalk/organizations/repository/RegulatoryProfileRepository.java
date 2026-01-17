// src/main/java/com/ledgertalk/organizations/repository/RegulatoryProfileRepository.java
package com.ledgertalk.organizations.repository;

import com.ledgertalk.organizations.entity.RegulatoryProfile;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface RegulatoryProfileRepository extends JpaRepository<RegulatoryProfile, UUID> {

    Optional<RegulatoryProfile> findByOrganizationId(UUID orgId);
}