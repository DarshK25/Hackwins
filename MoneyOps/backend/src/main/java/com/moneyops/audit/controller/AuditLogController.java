// src/main/java/com/moneyops/audit/controller/AuditLogController.java
package com.moneyops.audit.controller;

import com.moneyops.audit.dto.AuditLogDTO;
import com.moneyops.audit.entity.AuditLog;
import com.moneyops.audit.service.AuditLogService;
import com.moneyops.shared.dto.ApiResponse;
import com.moneyops.shared.dto.PageResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;

@RestController
@RequestMapping("/api/audit")
@RequiredArgsConstructor
@Tag(name = "Audit", description = "Audit log management endpoints")
public class AuditLogController {

    private final AuditLogService auditLogService;

    @GetMapping
    @Operation(summary = "Get all audit logs for the organization (paginated)")
    public ResponseEntity<ApiResponse<PageResponse<AuditLogDTO>>> getAllAuditLogs(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        // Clamp page size to prevent abuse
        int clampedSize = Math.min(Math.max(size, 1), 100);

        PageResponse<AuditLogDTO> pageResponse = auditLogService.getAllAuditLogsPaginated(page, clampedSize);
        return ResponseEntity.ok(ApiResponse.success(pageResponse));
    }

    @GetMapping("/entity/{entityType}")
    @Operation(summary = "Get audit logs for a specific entity type (paginated)")
    public ResponseEntity<ApiResponse<PageResponse<AuditLogDTO>>> getAuditLogsByEntityType(
            @PathVariable String entityType,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        int clampedSize = Math.min(Math.max(size, 1), 100);
        PageResponse<AuditLogDTO> pageResponse = auditLogService.getAuditLogsByEntityTypePaginated(entityType, page, clampedSize);
        return ResponseEntity.ok(ApiResponse.success(pageResponse));
    }

    @GetMapping("/entity/{entityType}/{entityId}")
    @Operation(summary = "Get audit logs for a specific entity (paginated)")
    public ResponseEntity<ApiResponse<PageResponse<AuditLogDTO>>> getAuditLogsByEntityId(
            @PathVariable String entityType,
            @PathVariable String entityId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        int clampedSize = Math.min(Math.max(size, 1), 100);
        // entityType is accepted for URL semantics but we query by entityId
        PageResponse<AuditLogDTO> pageResponse = auditLogService.getAuditLogsByEntityIdPaginated(entityId, page, clampedSize);
        return ResponseEntity.ok(ApiResponse.success(pageResponse));
    }

    @GetMapping("/user/{userId}")
    @Operation(summary = "Get audit logs for a specific user (paginated)")
    public ResponseEntity<ApiResponse<PageResponse<AuditLogDTO>>> getAuditLogsByUserId(
            @PathVariable String userId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        int clampedSize = Math.min(Math.max(size, 1), 100);
        PageResponse<AuditLogDTO> pageResponse = auditLogService.getAuditLogsByUserIdPaginated(userId, page, clampedSize);
        return ResponseEntity.ok(ApiResponse.success(pageResponse));
    }

    @GetMapping("/operation/{operation}")
    @Operation(summary = "Get audit logs for a specific operation (paginated)")
    public ResponseEntity<ApiResponse<PageResponse<AuditLogDTO>>> getAuditLogsByOperation(
            @PathVariable AuditLog.Operation operation,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        int clampedSize = Math.min(Math.max(size, 1), 100);
        PageResponse<AuditLogDTO> pageResponse = auditLogService.getAuditLogsByOperationPaginated(operation, page, clampedSize);
        return ResponseEntity.ok(ApiResponse.success(pageResponse));
    }

    @GetMapping("/daterange")
    @Operation(summary = "Get audit logs within a date range (paginated)")
    public ResponseEntity<ApiResponse<PageResponse<AuditLogDTO>>> getAuditLogsByDateRange(
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime start,
            @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime end,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        int clampedSize = Math.min(Math.max(size, 1), 100);
        PageResponse<AuditLogDTO> pageResponse = auditLogService.getAuditLogsByDateRangePaginated(start, end, page, clampedSize);
        return ResponseEntity.ok(ApiResponse.success(pageResponse));
    }
}
