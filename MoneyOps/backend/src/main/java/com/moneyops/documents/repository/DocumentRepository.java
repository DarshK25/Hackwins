package com.moneyops.documents.repository;

import com.moneyops.documents.entity.MoneyOpsDocument;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface DocumentRepository extends MongoRepository<MoneyOpsDocument, UUID> {

    List<MoneyOpsDocument> findByOrgId(UUID orgId);

    List<MoneyOpsDocument> findByLinkedEntityTypeAndLinkedEntityId(String linkedEntityType, UUID linkedEntityId);
}