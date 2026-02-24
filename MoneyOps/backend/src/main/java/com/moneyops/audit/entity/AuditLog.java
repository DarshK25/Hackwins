package com.moneyops.audit.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "audit_logs")
@Data
public class AuditLog {

    @Id
    private UUID id = UUID.randomUUID();

    private UUID orgId;
    private UUID userId;
    private String entityType;  // e.g. "User", "Invoice", "Client"
    private String entityId;    // UUID as string
    private Operation operation;
    private String oldValues;   // JSON string
    private String newValues;   // JSON string
    private String changes;     // JSON string
    private String ipAddress;
    private String userAgent;
    private LocalDateTime timestamp = LocalDateTime.now();

    public enum Operation {
        CREATE, UPDATE, DELETE
    }
}