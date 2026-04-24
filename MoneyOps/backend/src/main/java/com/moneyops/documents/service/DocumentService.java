package com.moneyops.documents.service;

import com.moneyops.documents.dto.DocumentUploadDTO;
import com.moneyops.documents.entity.MoneyOpsDocument;
import com.moneyops.documents.repository.DocumentRepository;
import com.moneyops.documents.storage.FirebaseStorageHelper;
import com.moneyops.shared.dto.PageResponse;
import com.moneyops.shared.exceptions.NotFoundException;
import com.moneyops.shared.exceptions.UnauthorizedException;
import com.moneyops.shared.exceptions.ValidationException;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class DocumentService {

    private static final Set<String> CONFIDENTIAL_TYPES = Set.of(
            "BANK_STATEMENT",
            "FINANCIAL",
            "PAYROLL",
            "TAX",
            "LEGAL",
            "KYC",
            "HR"
    );

    private final DocumentRepository documentRepository;
    private final FirebaseStorageHelper firebaseStorageHelper;

    public PageResponse<MoneyOpsDocument> getDocuments(String orgId, int page, int size, String type) {
        String resolvedOrgId = requireOrgId(orgId);
        PageRequest pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        Page<MoneyOpsDocument> resultPage = (type == null || type.isBlank())
                ? documentRepository.findByOrgIdAndDeletedAtIsNull(resolvedOrgId, pageable)
                : documentRepository.findByOrgIdAndTypeAndDeletedAtIsNull(resolvedOrgId, normalize(type), pageable);
        return PageResponse.from(resultPage);
    }

    public MoneyOpsDocument getDocumentById(String id, String orgId) {
        return findActiveDocument(id, requireOrgId(orgId));
    }

    @Transactional
    public MoneyOpsDocument uploadDocument(MultipartFile file, DocumentUploadDTO metadata, String orgId, String userId) {
        String resolvedOrgId = requireOrgId(orgId != null ? orgId : metadata != null ? metadata.getOrgId() : null);
        validateUpload(file, metadata);

        String documentId = UUID.randomUUID().toString();
        FirebaseStorageHelper.UploadResult uploadResult = firebaseStorageHelper.upload(resolvedOrgId, documentId, file);

        MoneyOpsDocument document = new MoneyOpsDocument();
        document.setId(documentId);
        document.setOrgId(resolvedOrgId);
        document.setName(resolveDocumentName(file, metadata));
        document.setType(normalize(defaultIfBlank(metadata.getType(), "OTHER")));
        document.setSize(file.getSize());
        document.setFirebasePath(uploadResult.firebasePath());
        document.setDownloadUrl(uploadResult.downloadUrl());
        document.setMimeType(defaultIfBlank(metadata.getMimeType(), file.getContentType()));
        document.setUploadedBy(userId);
        document.setLinkedEntityType(normalizeNullable(metadata.getLinkedEntityType()));
        document.setLinkedEntityId(trimToNull(metadata.getLinkedEntityId()));
        document.setConfidential(resolveConfidential(metadata));
        document.setCategory(trimToNull(metadata.getCategory()));
        document.setContentSummary(trimToNull(metadata.getContentSummary()));
        document.setDetectedDeadlines(metadata.getDetectedDeadlines() != null ? metadata.getDetectedDeadlines() : List.of());

        return documentRepository.save(document);
    }

    public List<MoneyOpsDocument> getDocumentsByEntity(String entityType, String entityId, String orgId) {
        return documentRepository.findByOrgIdAndLinkedEntityTypeAndLinkedEntityIdAndDeletedAtIsNull(
                requireOrgId(orgId),
                normalize(entityType),
                entityId
        );
    }

    @Transactional
    public void deleteDocument(String id, String orgId) {
        MoneyOpsDocument document = findActiveDocument(id, requireOrgId(orgId));
        document.setDeletedAt(LocalDateTime.now());
        documentRepository.save(document);
    }

    public String getDownloadUrl(String id, String orgId) {
        MoneyOpsDocument document = findActiveDocument(id, requireOrgId(orgId));
        if (document.getFirebasePath() != null && !document.getFirebasePath().isBlank()) {
            String signedUrl = firebaseStorageHelper.generateSignedUrl(document.getFirebasePath());
            document.setDownloadUrl(signedUrl);
            documentRepository.save(document);
            return signedUrl;
        }
        if (document.getDownloadUrl() != null && !document.getDownloadUrl().isBlank()) {
            return document.getDownloadUrl();
        }
        throw new NotFoundException("Document download URL not available");
    }

    private MoneyOpsDocument findActiveDocument(String id, String orgId) {
        return documentRepository.findByIdAndOrgIdAndDeletedAtIsNull(id, orgId)
                .orElseThrow(() -> new NotFoundException("Document", id));
    }

    private void validateUpload(MultipartFile file, DocumentUploadDTO metadata) {
        if (file == null || file.isEmpty()) {
            throw new ValidationException(List.of("Document file is required"));
        }
        if (metadata == null) {
            throw new ValidationException(List.of("Document metadata is required"));
        }
        if (metadata.getType() == null || metadata.getType().isBlank()) {
            throw new ValidationException(List.of("Document type is required"));
        }
    }

    private String requireOrgId(String orgId) {
        if (orgId == null || orgId.isBlank()) {
            throw new UnauthorizedException("Missing organization context");
        }
        return orgId;
    }

    private boolean resolveConfidential(DocumentUploadDTO metadata) {
        if (metadata.getIsConfidential() != null) {
            return metadata.getIsConfidential();
        }
        return CONFIDENTIAL_TYPES.contains(normalize(defaultIfBlank(metadata.getType(), "OTHER")));
    }

    private String resolveDocumentName(MultipartFile file, DocumentUploadDTO metadata) {
        String requestedName = trimToNull(metadata.getName());
        if (requestedName != null) {
            return requestedName;
        }
        return defaultIfBlank(file.getOriginalFilename(), "document");
    }

    private String defaultIfBlank(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isBlank() ? null : trimmed;
    }

    private String normalize(String value) {
        return value.trim().toUpperCase(Locale.ROOT);
    }

    private String normalizeNullable(String value) {
        String trimmed = trimToNull(value);
        return trimmed == null ? null : normalize(trimmed);
    }
}
