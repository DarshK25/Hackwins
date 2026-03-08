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
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentRepository documentRepository;

    public List<MoneyOpsDocument> getDocumentsByOrg(UUID orgId) {
        return documentRepository.findByOrgId(orgId);
    }

    public List<MoneyOpsDocument> getVisibleDocuments(UUID orgId, UUID userId, boolean showPrivate) {
        if (showPrivate) {
            // Private = Only those uploaded by this user marked as confidential
            return documentRepository.findByOrgIdAndUploadedByAndIsConfidential(orgId, userId, true);
        } else {
            // Shared = All documents in org NOT marked as confidential
            return documentRepository.findByOrgIdAndIsConfidential(orgId, false);
        }
    }

    public MoneyOpsDocument getDocumentById(UUID id) {
        return documentRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("Document not found with ID: " + id));
    }

    @Transactional
    public MoneyOpsDocument createDocumentMetadata(MoneyOpsDocument document) {
        document.setCreatedAt(LocalDateTime.now());
        if (document.getId() == null) {
            document.setId(UUID.randomUUID());
        }
        return documentRepository.save(document);
    }

    public List<MoneyOpsDocument> getDocumentsByEntity(String entityType, UUID entityId) {
        return documentRepository.findByLinkedEntityTypeAndLinkedEntityId(entityType, entityId);
    }

    @Transactional
    public void deleteDocument(UUID id) {
        if (!documentRepository.existsById(id)) {
            throw new NotFoundException("Document not found with ID: " + id);
        }
        documentRepository.deleteById(id);
    }
}