package com.moneyops.audit.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.index.Indexed;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "audit_logs")
@Data
public class AuditLog {

    @Id
    private String id;

    @Indexed
    private String orgId;      // 🔗 Tenant isolation
    
    @Indexed
    private String userId;     // Who performed the action
    
    private String entityType;  // INVOICE, CLIENT, etc.
    
    @Indexed
    private String entityId;    // The affected entity's ID
    
    private Operation operation; // CREATE, UPDATE, DELETE
    
    private String oldValues;    // JSON string of state BEFORE
    private String newValues;    // JSON string of state AFTER
    private String changes;      // JSON string of DIFF
    
    private String ipAddress;
    private String userAgent;
    
    @Indexed
    private LocalDateTime timestamp;

    /**
     * Auto-populate ID and timestamp before first save.
     * Using a regular method instead of @PostConstruct since entities
     * are not Spring-managed beans.
     */
    public AuditLog() {
        if (this.id == null) {
            this.id = UUID.randomUUID().toString();
        }
        if (this.timestamp == null) {
            this.timestamp = LocalDateTime.now();
        }
    }

    public enum Operation {
        CREATE, UPDATE, DELETE
    }
}