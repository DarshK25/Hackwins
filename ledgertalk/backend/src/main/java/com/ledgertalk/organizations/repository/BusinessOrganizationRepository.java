// src/main/java/com/ledgertalk/organizations/repository/BusinessOrganizationRepository.java
package com.ledgertalk.organizations.repository;

import com.ledgertalk.organizations.entity.BusinessOrganization;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface BusinessOrganizationRepository extends JpaRepository<BusinessOrganization, UUID> {

    Optional<BusinessOrganization> findByIdAndCreatedBy(UUID id, UUID createdBy);

    List<BusinessOrganization> findAllByCreatedBy(UUID createdBy);

    void deleteByIdAndCreatedBy(UUID id, UUID createdBy);

    boolean existsByIdAndCreatedBy(UUID id, UUID createdBy);

    Optional<BusinessOrganization> findByLegalNameAndCreatedBy(String legalName, UUID createdBy);

    // Search with filters
    List<BusinessOrganization> findByCreatedByAndLegalNameContainingIgnoreCase(UUID createdBy, String legalName);
}