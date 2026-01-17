// src/main/java/com/ledgertalk/audit/repository/AuditLogRepository.java
package com.ledgertalk.audit.repository;

import com.ledgertalk.audit.entity.AuditLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, UUID> {

    List<AuditLog> findByOrgIdOrderByTimestampDesc(UUID orgId);

    List<AuditLog> findByOrgIdAndEntityTypeOrderByTimestampDesc(UUID orgId, String entityType);

    List<AuditLog> findByOrgIdAndEntityIdOrderByTimestampDesc(UUID orgId, String entityId);

    List<AuditLog> findByOrgIdAndUserIdOrderByTimestampDesc(UUID orgId, UUID userId);

    @Query("SELECT a FROM AuditLog a WHERE a.orgId = :orgId AND a.timestamp BETWEEN :start AND :end ORDER BY a.timestamp DESC")
    List<AuditLog> findByOrgIdAndTimestampBetween(@Param("orgId") UUID orgId,
                                                  @Param("start") LocalDateTime start,
                                                  @Param("end") LocalDateTime end);

    @Query("SELECT a FROM AuditLog a WHERE a.orgId = :orgId AND a.operation = :operation ORDER BY a.timestamp DESC")
    List<AuditLog> findByOrgIdAndOperation(@Param("orgId") UUID orgId,
                                           @Param("operation") AuditLog.Operation operation);
}