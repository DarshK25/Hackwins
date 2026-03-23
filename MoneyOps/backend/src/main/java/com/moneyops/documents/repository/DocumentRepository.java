package com.moneyops.documents.repository;

import com.moneyops.documents.entity.MoneyOpsDocument;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DocumentRepository extends MongoRepository<MoneyOpsDocument, String> {

    List<MoneyOpsDocument> findByOrgIdAndDeletedAtIsNull(String orgId);
    List<MoneyOpsDocument> findByOrgIdAndIsConfidentialAndDeletedAtIsNull(String orgId, boolean isConfidential);
    List<MoneyOpsDocument> findByOrgIdAndUploadedByAndIsConfidentialAndDeletedAtIsNull(String orgId, String uploadedBy, boolean isConfidential);
    List<MoneyOpsDocument> findByLinkedEntityTypeAndLinkedEntityIdAndDeletedAtIsNull(String linkedEntityType, String linkedEntityId);
}