package com.moneyops.audit.repository;

import com.moneyops.audit.entity.AuditLog;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface AuditLogRepository extends MongoRepository<AuditLog, UUID> {

    List<AuditLog> findByOrgIdOrderByTimestampDesc(UUID orgId);

    List<AuditLog> findByOrgIdAndEntityTypeOrderByTimestampDesc(UUID orgId, String entityType);

    List<AuditLog> findByOrgIdAndEntityIdOrderByTimestampDesc(UUID orgId, String entityId);

    List<AuditLog> findByOrgIdAndUserIdOrderByTimestampDesc(UUID orgId, UUID userId);

    List<AuditLog> findByOrgIdAndOperation(UUID orgId, AuditLog.Operation operation);

    List<AuditLog> findByOrgIdAndTimestampBetween(UUID orgId, java.time.LocalDateTime start, java.time.LocalDateTime end);
}