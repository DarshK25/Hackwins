package com.moneyops.documents.controller;

import com.moneyops.documents.dto.DocumentUploadDTO;
import com.moneyops.documents.entity.MoneyOpsDocument;
import com.moneyops.documents.service.DocumentService;
import com.moneyops.shared.dto.ApiResponse;
import com.moneyops.shared.dto.PageResponse;
import com.moneyops.shared.utils.OrgContext;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;

    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<MoneyOpsDocument>>> getDocuments(
            @RequestParam(required = false) String orgId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String type
    ) {
        String resolvedOrgId = resolveOrgId(orgId);
        PageResponse<MoneyOpsDocument> documents = documentService.getDocuments(resolvedOrgId, page, size, type);
        return ResponseEntity.ok(ApiResponse.success(documents));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<MoneyOpsDocument>> getDocument(
            @PathVariable String id,
            @RequestParam(required = false) String orgId
    ) {
        String resolvedOrgId = resolveOrgId(orgId);
        return ResponseEntity.ok(ApiResponse.success(documentService.getDocumentById(id, resolvedOrgId)));
    }

    @PostMapping(value = "/upload", consumes = "multipart/form-data")
    public ResponseEntity<ApiResponse<MoneyOpsDocument>> uploadDocument(
            @RequestPart("file") MultipartFile file,
            @RequestPart("metadata") DocumentUploadDTO metadata,
            @RequestParam(required = false) String orgId
    ) {
        String resolvedOrgId = resolveOrgId(orgId != null ? orgId : metadata.getOrgId());
        String userId = OrgContext.getUserId();
        MoneyOpsDocument document = documentService.uploadDocument(file, metadata, resolvedOrgId, userId);
        return ResponseEntity.ok(ApiResponse.success("Document uploaded successfully", document));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteDocument(
            @PathVariable String id,
            @RequestParam(required = false) String orgId
    ) {
        documentService.deleteDocument(id, resolveOrgId(orgId));
        return ResponseEntity.ok(ApiResponse.success("Document deleted successfully", null));
    }

    @GetMapping("/entity/{entityType}/{entityId}")
    public ResponseEntity<ApiResponse<List<MoneyOpsDocument>>> getDocumentsByEntity(
            @PathVariable String entityType,
            @PathVariable String entityId,
            @RequestParam(required = false) String orgId
    ) {
        return ResponseEntity.ok(ApiResponse.success(
                documentService.getDocumentsByEntity(entityType, entityId, resolveOrgId(orgId))
        ));
    }

    @GetMapping("/{id}/download")
    public ResponseEntity<ApiResponse<Map<String, String>>> getDownloadUrl(
            @PathVariable String id,
            @RequestParam(required = false) String orgId
    ) {
        String url = documentService.getDownloadUrl(id, resolveOrgId(orgId));
        return ResponseEntity.ok(ApiResponse.success(Map.of("downloadUrl", url)));
    }

    private String resolveOrgId(String fallbackOrgId) {
        return OrgContext.getOrgId() != null ? OrgContext.getOrgId() : fallbackOrgId;
    }
}
