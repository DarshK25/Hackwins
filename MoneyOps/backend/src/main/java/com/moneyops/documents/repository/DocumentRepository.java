package com.moneyops.documents.repository;

import com.moneyops.documents.entity.MoneyOpsDocument;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface DocumentRepository extends MongoRepository<MoneyOpsDocument, String> {

    List<MoneyOpsDocument> findByOrgIdAndDeletedAtIsNull(String orgId);
    Page<MoneyOpsDocument> findByOrgIdAndDeletedAtIsNull(String orgId, Pageable pageable);
    Page<MoneyOpsDocument> findByOrgIdAndTypeAndDeletedAtIsNull(String orgId, String type, Pageable pageable);
    List<MoneyOpsDocument> findByOrgIdAndIsConfidentialAndDeletedAtIsNull(String orgId, boolean isConfidential);
    List<MoneyOpsDocument> findByOrgIdAndUploadedByAndIsConfidentialAndDeletedAtIsNull(String orgId, String uploadedBy, boolean isConfidential);
    List<MoneyOpsDocument> findByOrgIdAndLinkedEntityTypeAndLinkedEntityIdAndDeletedAtIsNull(String orgId, String linkedEntityType, String linkedEntityId);
    Optional<MoneyOpsDocument> findByIdAndOrgIdAndDeletedAtIsNull(String id, String orgId);
}
