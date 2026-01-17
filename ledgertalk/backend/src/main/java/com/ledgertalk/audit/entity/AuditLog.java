// src/main/java/com/ledgertalk/audit/entity/AuditLog.java
package com.ledgertalk.audit.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "audit_logs")
@Data
public class AuditLog {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private UUID orgId;

    @Column(nullable = false)
    private UUID userId;

    @Column(nullable = false)
    private String entityType; // e.g., "User", "Invoice", "Client"

    @Column(nullable = false)
    private String entityId; // UUID as string

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Operation operation; // CREATE, UPDATE, DELETE

    @Column(columnDefinition = "TEXT")
    private String oldValues; // JSON string of old values

    @Column(columnDefinition = "TEXT")
    private String newValues; // JSON string of new values

    @Column(columnDefinition = "TEXT")
    private String changes; // JSON string of what changed

    private String ipAddress;

    private String userAgent;

    @Column(nullable = false)
    private LocalDateTime timestamp = LocalDateTime.now();

    public enum Operation {
        CREATE, UPDATE, DELETE
    }
}