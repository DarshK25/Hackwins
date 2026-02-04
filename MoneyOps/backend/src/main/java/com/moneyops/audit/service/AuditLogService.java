// src/main/java/com/moneyops/audit/service/AuditLogService.java
package com.moneyops.audit.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.moneyops.audit.entity.AuditLog;
import com.moneyops.audit.repository.AuditLogRepository;
import com.moneyops.shared.utils.OrgContext;
import com.moneyops.shared.utils.SecurityUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;

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
            auditLog.setUserId(SecurityUtil.getCurrentUserId());
            auditLog.setEntityType(entityType);
            auditLog.setEntityId(entityId);
            auditLog.setOperation(operation);

            if (oldEntity != null) {
                auditLog.setOldValues(objectMapper.writeValueAsString(oldEntity));
            }

            if (newEntity != null) {
                auditLog.setNewValues(objectMapper.writeValueAsString(newEntity));
            }

            if (changes != null && !changes.isEmpty()) {
                auditLog.setChanges(objectMapper.writeValueAsString(changes));
            }

            // TODO: Add IP address and user agent from request context
            auditLog.setIpAddress("TODO");
            auditLog.setUserAgent("TODO");

            auditLogRepository.save(auditLog);

            log.info("Audit logged: {} {} {} by user {}", operation, entityType, entityId,
                    SecurityUtil.getCurrentUserId());

        } catch (Exception e) {
            log.error("Failed to log audit event", e);
        }
    }

    private Map<String, Object> calculateChanges(Object oldEntity, Object newEntity) {
        // TODO: Implement proper change calculation using reflection or diff libraries
        // For now, return empty map
        return Map.of();
    }

    // Query methods
    public List<AuditLog> getAllAuditLogs() {
        return auditLogRepository.findByOrgIdOrderByTimestampDesc(OrgContext.getOrgId());
    }

    public List<AuditLog> getAuditLogsByEntityType(String entityType) {
        return auditLogRepository.findByOrgIdAndEntityTypeOrderByTimestampDesc(OrgContext.getOrgId(), entityType);
    }

    public List<AuditLog> getAuditLogsByEntityId(String entityId) {
        return auditLogRepository.findByOrgIdAndEntityIdOrderByTimestampDesc(OrgContext.getOrgId(), entityId);
    }

    public List<AuditLog> getAuditLogsByUserId(UUID userId) {
        return auditLogRepository.findByOrgIdAndUserIdOrderByTimestampDesc(OrgContext.getOrgId(), userId);
    }

    public List<AuditLog> getAuditLogsByDateRange(LocalDateTime start, LocalDateTime end) {
        return auditLogRepository.findByOrgIdAndTimestampBetween(OrgContext.getOrgId(), start, end);
    }

    public List<AuditLog> getAuditLogsByOperation(AuditLog.Operation operation) {
        return auditLogRepository.findByOrgIdAndOperation(OrgContext.getOrgId(), operation);
    }
}