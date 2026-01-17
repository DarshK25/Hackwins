package com.ledgertalk.documents.service;

import com.ledgertalk.documents.entity.Document;
import com.ledgertalk.documents.repository.DocumentRepository;
import com.ledgertalk.shared.dto.PageResponse;
import com.ledgertalk.shared.exceptions.NotFoundException;
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

    public List<Document> getDocumentsByOrg(UUID orgId) {
        return documentRepository.findByOrgId(orgId);
    }

    public Document getDocumentById(UUID id) {
        return documentRepository.findById(id)
                .orElseThrow(() -> new NotFoundException("Document not found with ID: " + id));
    }

    @Transactional
    public Document createDocumentMetadata(Document document) {
        document.setCreatedAt(LocalDateTime.now());
        if (document.getId() == null) {
            document.setId(UUID.randomUUID());
        }
        return documentRepository.save(document);
    }

    public List<Document> getDocumentsByEntity(String entityType, UUID entityId) {
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