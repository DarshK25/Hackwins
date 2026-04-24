package com.moneyops.audit.repository;

import com.moneyops.audit.entity.AuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.mongodb.repository.MongoRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AuditLogRepository extends MongoRepository<AuditLog, String> {

    // ── Legacy non-paginated queries (backward compatibility) ────────────────

    List<AuditLog> findByOrgIdOrderByTimestampDesc(String orgId);

    List<AuditLog> findByOrgIdAndEntityTypeOrderByTimestampDesc(String orgId, String entityType);

    List<AuditLog> findByOrgIdAndEntityIdOrderByTimestampDesc(String orgId, String entityId);

    List<AuditLog> findByOrgIdAndUserIdOrderByTimestampDesc(String orgId, String userId);

    List<AuditLog> findByOrgIdAndOperationOrderByTimestampDesc(String orgId, AuditLog.Operation operation);

    List<AuditLog> findByOrgIdAndTimestampBetweenOrderByTimestampDesc(String orgId, LocalDateTime start, LocalDateTime end);

    // ── Paginated queries ────────────────────────────────────────────────────

    Page<AuditLog> findByOrgId(String orgId, Pageable pageable);

    Page<AuditLog> findByOrgIdAndEntityType(String orgId, String entityType, Pageable pageable);

    Page<AuditLog> findByOrgIdAndEntityId(String orgId, String entityId, Pageable pageable);

    Page<AuditLog> findByOrgIdAndUserId(String orgId, String userId, Pageable pageable);

    Page<AuditLog> findByOrgIdAndOperation(String orgId, AuditLog.Operation operation, Pageable pageable);

    Page<AuditLog> findByOrgIdAndTimestampBetween(String orgId, LocalDateTime start, LocalDateTime end, Pageable pageable);
}