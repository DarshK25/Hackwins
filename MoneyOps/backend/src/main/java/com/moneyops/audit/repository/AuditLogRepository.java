package com.moneyops.audit.repository;

import com.moneyops.audit.entity.AuditLog;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface AuditLogRepository extends MongoRepository<AuditLog, String> {

    List<AuditLog> findByOrgIdOrderByTimestampDesc(String orgId);

    List<AuditLog> findByOrgIdAndEntityTypeOrderByTimestampDesc(String orgId, String entityType);

    List<AuditLog> findByOrgIdAndEntityIdOrderByTimestampDesc(String orgId, String entityId);

    List<AuditLog> findByOrgIdAndUserIdOrderByTimestampDesc(String orgId, String userId);

    List<AuditLog> findByOrgIdAndOperation(String orgId, AuditLog.Operation operation);

    List<AuditLog> findByOrgIdAndTimestampBetween(String orgId, java.time.LocalDateTime start, java.time.LocalDateTime end);
}