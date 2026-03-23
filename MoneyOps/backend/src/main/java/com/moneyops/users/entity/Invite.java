package com.moneyops.users.entity;

import jakarta.annotation.PostConstruct;
import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "invites")
@Data
public class Invite {

    @Id
    private String id;

    @Indexed
    private String orgId;      // 🔗 Tenant isolation
    
    @Indexed
    private String email;
    
    private User.Role role;
    private String token;
    private LocalDateTime expiresAt;
    private InviteStatus status = InviteStatus.PENDING;
    
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private String createdBy;
    private LocalDateTime deletedAt; // ✨ Soft delete support

    @PostConstruct
    public void generateId() {
        if (this.id == null) {
            this.id = UUID.randomUUID().toString();
        }
    }

    public enum InviteStatus {
        PENDING, ACCEPTED, EXPIRED
    }
}