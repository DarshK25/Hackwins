package com.moneyops.users.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "invites")
@Data
public class Invite {

    @Id
    private UUID id = UUID.randomUUID();

    private UUID orgId;
    private String email;
    private User.Role role;
    private String token;
    private LocalDateTime expiresAt;
    private InviteStatus status = InviteStatus.PENDING;
    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt;
    private UUID createdBy;

    public enum InviteStatus {
        PENDING, ACCEPTED, EXPIRED
    }
}