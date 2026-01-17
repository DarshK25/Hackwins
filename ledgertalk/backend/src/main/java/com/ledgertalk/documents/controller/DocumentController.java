package com.ledgertalk.documents.controller;

import com.ledgertalk.documents.entity.Document;
import com.ledgertalk.documents.service.DocumentService;
import com.ledgertalk.shared.dto.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
@Tag(name = "Documents", description = "Document management endpoints")
public class DocumentController {

    private final DocumentService documentService;

    @GetMapping("/org/{orgId}")
    @Operation(summary = "Get all documents for an organization")
    public ResponseEntity<ApiResponse<List<Document>>> getDocumentsByOrg(@PathVariable UUID orgId) {
        return ResponseEntity.ok(ApiResponse.success(documentService.getDocumentsByOrg(orgId)));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get document by ID")
    public ResponseEntity<ApiResponse<Document>> getDocumentById(@PathVariable UUID id) {
        return ResponseEntity.ok(ApiResponse.success(documentService.getDocumentById(id)));
    }

    @PostMapping
    @Operation(summary = "Create document metadata")
    public ResponseEntity<ApiResponse<Document>> createDocument(@RequestBody Document document) {
        return ResponseEntity.ok(ApiResponse.success(documentService.createDocumentMetadata(document)));
    }

    @GetMapping("/entity/{entityType}/{entityId}")
    @Operation(summary = "Get documents linked to a specific entity")
    public ResponseEntity<ApiResponse<List<Document>>> getDocumentsByEntity(
            @PathVariable String entityType,
            @PathVariable UUID entityId) {
        return ResponseEntity.ok(ApiResponse.success(documentService.getDocumentsByEntity(entityType, entityId)));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "Delete document")
    public ResponseEntity<ApiResponse<Void>> deleteDocument(@PathVariable UUID id) {
        documentService.deleteDocument(id);
        return ResponseEntity.ok(ApiResponse.success(null));
    }
}