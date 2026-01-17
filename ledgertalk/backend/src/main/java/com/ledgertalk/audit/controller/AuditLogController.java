// src/main/java/com/ledgertalk/audit/controller/AuditLogController.java
package com.ledgertalk.audit.controller;

import com.ledgertalk.audit.entity.AuditLog;
import com.ledgertalk.audit.service.AuditLogService;
import com.ledgertalk.shared.dto.ApiResponse;
import com.ledgertalk.shared.dto.PageResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/audit")
@RequiredArgsConstructor
@Tag(name = "Audit", description = "Audit log management endpoints")
public class AuditLogController {

    private final AuditLogService auditLogService;

    @GetMapping
    @Operation(summary = "Get all audit logs for the organization")
    public ResponseEntity<ApiResponse<PageResponse<AuditLog>>> getAllAuditLogs(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "50") int size) {

        List<AuditLog> logs = auditLogService.getAllAuditLogs();
        // TODO: Implement pagination
        PageResponse<AuditLog> pageResponse = PageResponse.<AuditLog>builder()
                .content(logs)
                .pageNumber(page)
                .pageSize(size)
                .totalElements(logs.size())
                .totalPages(1)
                .build();

        return ResponseEntity.ok(ApiResponse.success(pageResponse));
    }

    @GetMapping("/entity/{entityType}")
    @Operation(summary = "Get audit logs for a specific entity type")
    public ResponseEntity<ApiResponse<List<AuditLog>>> getAuditLogsByEntityType(
            @PathVariable String entityType) {

        List<AuditLog> logs = auditLogService.getAuditLogsByEntityType(entityType);
        return ResponseEntity.ok(ApiResponse.success(logs));
    }

    @GetMapping("/entity/{entityType}/{entityId}")
    @Operation(summary = "Get audit logs for a specific entity")
    public ResponseEntity<ApiResponse<List<AuditLog>>> getAuditLogsByEntityId(
            @PathVariable String entityType,
            @PathVariable String entityId) {

        List<AuditLog> logs = auditLogService.getAuditLogsByEntityId(entityId);
        return ResponseEntity.ok(ApiResponse.success(logs));
    }

    @GetMapping("/user/{userId}")
    @Operation(summary = "Get audit logs for a specific user")
    public ResponseEntity<ApiResponse<List<AuditLog>>> getAuditLogsByUserId(
            @PathVariable UUID userId) {

        List<AuditLog> logs = auditLogService.getAuditLogsByUserId(userId);
        return ResponseEntity.ok(ApiResponse.success(logs));
    }

    @GetMapping("/operation/{operation}")
    @Operation(summary = "Get audit logs for a specific operation")
    public ResponseEntity<ApiResponse<List<AuditLog>>> getAuditLogsByOperation(
            @PathVariable AuditLog.Operation operation) {

        List<AuditLog> logs = auditLogService.getAuditLogsByOperation(operation);
        return ResponseEntity.ok(ApiResponse.success(logs));
    }

    @GetMapping("/daterange")
    @Operation(summary = "Get audit logs within a date range")
    public ResponseEntity<ApiResponse<List<AuditLog>>> getAuditLogsByDateRange(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime start,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime end) {

        List<AuditLog> logs = auditLogService.getAuditLogsByDateRange(start, end);
        return ResponseEntity.ok(ApiResponse.success(logs));
    }
}