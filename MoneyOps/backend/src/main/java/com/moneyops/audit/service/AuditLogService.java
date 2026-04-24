// src/main/java/com/moneyops/audit/service/AuditLogService.java
package com.moneyops.audit.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.moneyops.audit.dto.AuditLogDTO;
import com.moneyops.audit.entity.AuditLog;
import com.moneyops.audit.repository.AuditLogRepository;
import com.moneyops.shared.dto.PageResponse;
import com.moneyops.shared.utils.OrgContext;
import com.moneyops.shared.utils.RequestContext;
import com.moneyops.shared.utils.SecurityUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuditLogService {

    private final AuditLogRepository auditLogRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public void logCreate(String entityType, String entityId, Object newEntity) {
        log(AuditLog.Operation.CREATE, entityType, entityId, null, newEntity, null);
    }

    @Transactional
    public void logUpdate(String entityType, String entityId, Object oldEntity, Object newEntity) {
        Map<String, Object> changes = calculateChanges(oldEntity, newEntity);
        log(AuditLog.Operation.UPDATE, entityType, entityId, oldEntity, newEntity, changes);
    }

    @Transactional
    public void logDelete(String entityType, String entityId, Object oldEntity) {
        log(AuditLog.Operation.DELETE, entityType, entityId, oldEntity, null, null);
    }

    private void log(AuditLog.Operation operation, String entityType, String entityId,
                     Object oldEntity, Object newEntity, Map<String, Object> changes) {
        try {
            AuditLog auditLog = new AuditLog();
            auditLog.setOrgId(OrgContext.getOrgId());
            // For AI/voice service calls, Spring Security principal may be the service name.
            // We must attribute actions to the real user via OrgContext.
            String currentUserId = OrgContext.getUserId();
            if (currentUserId == null || currentUserId.isBlank()) {
                currentUserId = SecurityUtil.getCurrentUserId();
            }
            auditLog.setUserId(currentUserId);
            auditLog.setEntityType(entityType);
            auditLog.setEntityId(entityId);
            auditLog.setOperation(operation);

            // Null-safe JSON serialization for old/new values
            auditLog.setOldValues(safeSerialize(oldEntity));
            auditLog.setNewValues(safeSerialize(newEntity));

            if (changes != null && !changes.isEmpty()) {
                auditLog.setChanges(safeSerialize(changes));
            }

            // Capture IP address and User-Agent from the request context
            String ip = RequestContext.getIpAddress();
            String ua = RequestContext.getUserAgent();
            auditLog.setIpAddress(ip != null ? ip : "system");
            auditLog.setUserAgent(ua != null ? ua : "system");

            auditLogRepository.save(auditLog);

            log.info("Audit logged: {} {} {} by user {} from {}",
                    operation, entityType, entityId, currentUserId, ip);

        } catch (Exception e) {
            log.error("Failed to log audit event", e);
        }
    }

    /**
     * Safely serialize an object to JSON string.
     * Handles null values, circular references, and serialization errors gracefully.
     */
    private String safeSerialize(Object obj) {
        if (obj == null) return null;
        // Already a String — could be pre-serialized JSON
        if (obj instanceof String s) {
            return s.isBlank() ? null : s;
        }
        try {
            return objectMapper.writeValueAsString(obj);
        } catch (JsonProcessingException e) {
            log.warn("Failed to serialize audit value: {}", e.getMessage());
            // Fallback: store toString() representation wrapped as JSON string
            return "\"" + obj.toString().replace("\"", "\\\"") + "\"";
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> calculateChanges(Object oldEntity, Object newEntity) {
        try {
            Map<String, Object> oldMap = objectMapper.convertValue(oldEntity, Map.class);
            Map<String, Object> newMap = objectMapper.convertValue(newEntity, Map.class);
            if (oldMap == null || newMap == null) return Map.of();

            Map<String, Object> diff = new LinkedHashMap<>();
            for (Map.Entry<String, Object> entry : newMap.entrySet()) {
                Object oldVal = oldMap.get(entry.getKey());
                Object newVal = entry.getValue();
                if (oldVal == null && newVal == null) continue;
                if (oldVal == null || !oldVal.equals(newVal)) {
                    diff.put(entry.getKey(), Map.of(
                            "old", oldVal != null ? oldVal : "null",
                            "new", newVal != null ? newVal : "null"
                    ));
                }
            }
            return diff;
        } catch (Exception e) {
            log.warn("Failed to calculate changes: {}", e.getMessage());
            return Map.of();
        }
    }

    // ── Paginated query methods ──────────────────────────────────────────────

    public PageResponse<AuditLogDTO> getAllAuditLogsPaginated(int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<AuditLog> logPage = auditLogRepository.findByOrgId(OrgContext.getOrgId(), pageable);
        return toPageResponse(logPage);
    }

    public PageResponse<AuditLogDTO> getAuditLogsByEntityTypePaginated(String entityType, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<AuditLog> logPage = auditLogRepository.findByOrgIdAndEntityType(OrgContext.getOrgId(), entityType, pageable);
        return toPageResponse(logPage);
    }

    public PageResponse<AuditLogDTO> getAuditLogsByEntityIdPaginated(String entityId, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<AuditLog> logPage = auditLogRepository.findByOrgIdAndEntityId(OrgContext.getOrgId(), entityId, pageable);
        return toPageResponse(logPage);
    }

    public PageResponse<AuditLogDTO> getAuditLogsByUserIdPaginated(String userId, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<AuditLog> logPage = auditLogRepository.findByOrgIdAndUserId(OrgContext.getOrgId(), userId, pageable);
        return toPageResponse(logPage);
    }

    public PageResponse<AuditLogDTO> getAuditLogsByOperationPaginated(AuditLog.Operation operation, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<AuditLog> logPage = auditLogRepository.findByOrgIdAndOperation(OrgContext.getOrgId(), operation, pageable);
        return toPageResponse(logPage);
    }

    public PageResponse<AuditLogDTO> getAuditLogsByDateRangePaginated(LocalDateTime start, LocalDateTime end, int page, int size) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<AuditLog> logPage = auditLogRepository.findByOrgIdAndTimestampBetween(OrgContext.getOrgId(), start, end, pageable);
        return toPageResponse(logPage);
    }

    private PageResponse<AuditLogDTO> toPageResponse(Page<AuditLog> page) {
        List<AuditLogDTO> dtos = page.getContent().stream()
                .map(AuditLogDTO::from)
                .toList();
        return PageResponse.<AuditLogDTO>builder()
                .content(dtos)
                .pageNumber(page.getNumber())
                .pageSize(page.getSize())
                .totalElements(page.getTotalElements())
                .totalPages(page.getTotalPages())
                .first(page.isFirst())
                .last(page.isLast())
                .build();
    }

    // ── Legacy non-paginated methods (kept for backward compatibility) ───────

    public List<AuditLog> getAllAuditLogs() {
        return auditLogRepository.findByOrgIdOrderByTimestampDesc(OrgContext.getOrgId());
    }

    public List<AuditLog> getAuditLogsByEntityType(String entityType) {
        return auditLogRepository.findByOrgIdAndEntityTypeOrderByTimestampDesc(OrgContext.getOrgId(), entityType);
    }

    public List<AuditLog> getAuditLogsByEntityId(String entityId) {
        return auditLogRepository.findByOrgIdAndEntityIdOrderByTimestampDesc(OrgContext.getOrgId(), entityId);
    }

    public List<AuditLog> getAuditLogsByUserId(String userId) {
        return auditLogRepository.findByOrgIdAndUserIdOrderByTimestampDesc(OrgContext.getOrgId(), userId);
    }

    public List<AuditLog> getAuditLogsByDateRange(LocalDateTime start, LocalDateTime end) {
        return auditLogRepository.findByOrgIdAndTimestampBetweenOrderByTimestampDesc(OrgContext.getOrgId(), start, end);
    }

    public List<AuditLog> getAuditLogsByOperation(AuditLog.Operation operation) {
        return auditLogRepository.findByOrgIdAndOperationOrderByTimestampDesc(OrgContext.getOrgId(), operation);
    }
}
