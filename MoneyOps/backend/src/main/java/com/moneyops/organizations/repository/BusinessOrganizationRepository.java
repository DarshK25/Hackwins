package com.moneyops.organizations.repository;

import com.moneyops.organizations.entity.BusinessOrganization;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface BusinessOrganizationRepository extends MongoRepository<BusinessOrganization, String> {

    Optional<BusinessOrganization> findByIdAndDeletedAtIsNull(String id);
    Optional<BusinessOrganization> findByIdAndCreatedByAndDeletedAtIsNull(String id, String createdBy);
    List<BusinessOrganization> findAllByCreatedByAndDeletedAtIsNull(String createdBy);
    void deleteByIdAndCreatedBy(String id, String createdBy);
    boolean existsByIdAndCreatedByAndDeletedAtIsNull(String id, String createdBy);
    Optional<BusinessOrganization> findByLegalNameAndCreatedByAndDeletedAtIsNull(String legalName, String createdBy);
    List<BusinessOrganization> findByCreatedByAndLegalNameContainingIgnoreCaseAndDeletedAtIsNull(String createdBy, String legalName);
}