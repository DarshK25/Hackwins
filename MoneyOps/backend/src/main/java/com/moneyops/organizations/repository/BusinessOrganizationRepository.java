package com.moneyops.organizations.repository;

import com.moneyops.organizations.entity.BusinessOrganization;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface BusinessOrganizationRepository extends MongoRepository<BusinessOrganization, UUID> {

    Optional<BusinessOrganization> findByIdAndCreatedBy(UUID id, UUID createdBy);
    List<BusinessOrganization> findAllByCreatedBy(UUID createdBy);
    void deleteByIdAndCreatedBy(UUID id, UUID createdBy);
    boolean existsByIdAndCreatedBy(UUID id, UUID createdBy);
    Optional<BusinessOrganization> findByLegalNameAndCreatedBy(String legalName, UUID createdBy);
    List<BusinessOrganization> findByCreatedByAndLegalNameContainingIgnoreCase(UUID createdBy, String legalName);
}