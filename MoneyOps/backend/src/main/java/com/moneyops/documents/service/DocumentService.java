package com.moneyops.documents.service;

import com.moneyops.documents.entity.MoneyOpsDocument;
import com.moneyops.documents.repository.DocumentRepository;
import com.moneyops.shared.dto.PageResponse;
import com.moneyops.shared.exceptions.NotFoundException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile; // Assuming file upload
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentRepository documentRepository;

    public List<MoneyOpsDocument> getDocumentsByOrg(String orgId) {
        return documentRepository.findByOrgIdAndDeletedAtIsNull(orgId);
    }

    public List<MoneyOpsDocument> getVisibleDocuments(String orgId, String userId, boolean showPrivate) {
        if (showPrivate) {
            return documentRepository.findByOrgIdAndUploadedByAndIsConfidentialAndDeletedAtIsNull(orgId, userId, true);
        } else {
            return documentRepository.findByOrgIdAndIsConfidentialAndDeletedAtIsNull(orgId, false);
        }
    }

    public MoneyOpsDocument getDocumentById(String id) {
        return documentRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("Document not found with ID: " + id));
    }

    @Transactional
    public MoneyOpsDocument createDocumentMetadata(MoneyOpsDocument document) {
        if (document.getId() == null) {
            document.setId(java.util.UUID.randomUUID().toString());
        }
        return documentRepository.save(document);
    }

    public List<MoneyOpsDocument> getDocumentsByEntity(String entityType, String entityId) {
        return documentRepository.findByLinkedEntityTypeAndLinkedEntityIdAndDeletedAtIsNull(entityType, entityId);
    }

    @Transactional
    public void deleteDocument(String id) {
        MoneyOpsDocument document = documentRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("Document not found with ID: " + id));
        
        document.setDeletedAt(LocalDateTime.now());
        documentRepository.save(document);
    }
}