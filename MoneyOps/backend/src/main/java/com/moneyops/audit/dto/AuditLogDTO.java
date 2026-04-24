package com.moneyops.audit.dto;

import com.moneyops.audit.entity.AuditLog;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * DTO that safely exposes audit log data to the frontend,
 * with null-safe values serialization.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AuditLogDTO {

    private String id;
    private String orgId;
    private String userId;
    private String entityType;
    private String entityId;
    private String operation;
    private String oldValues;
    private String newValues;
    private String changes;
    private String ipAddress;
    private String userAgent;
    private LocalDateTime timestamp;

    /**
     * Convert entity → DTO with null-safe serialization.
     */
    public static AuditLogDTO from(AuditLog entity) {
        if (entity == null) return null;

        return AuditLogDTO.builder()
                .id(entity.getId())
                .orgId(entity.getOrgId())
                .userId(entity.getUserId())
                .entityType(entity.getEntityType())
                .entityId(entity.getEntityId())
                .operation(entity.getOperation() != null ? entity.getOperation().name() : null)
                .oldValues(sanitizeJson(entity.getOldValues()))
                .newValues(sanitizeJson(entity.getNewValues()))
                .changes(sanitizeJson(entity.getChanges()))
                .ipAddress(entity.getIpAddress())
                .userAgent(entity.getUserAgent())
                .timestamp(entity.getTimestamp())
                .build();
    }

    /**
     * Ensure JSON strings are valid. Return null for empty/blank/invalid strings
     * rather than corrupt data.
     */
    private static String sanitizeJson(String json) {
        if (json == null || json.isBlank()) return null;
        String trimmed = json.trim();
        // Quick check: valid JSON should start with { or [ or "
        if (trimmed.startsWith("{") || trimmed.startsWith("[") || trimmed.startsWith("\"")) {
            return trimmed;
        }
        // Wrap non-JSON strings as a JSON string value
        return "\"" + trimmed.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }
}
