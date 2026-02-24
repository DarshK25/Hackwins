package com.moneyops.users.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "users")
@Data
public class User {

    @Id
    private UUID id = UUID.randomUUID();

    private UUID orgId;
    private String name;

    @Indexed(unique = true)
    private String email;

    private String phone;
    private Role role = Role.STAFF;
    private Status status = Status.ACTIVE;
    private String passwordHash;

    // Clerk user ID — stored so we can look up a user by their Clerk token
    private String clerkId;

    // true once the user has completed onboarding
    private boolean onboardingComplete = false;

    private LocalDateTime lastLoginAt;
    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();
    private UUID createdBy;
    private UUID updatedBy;

    public enum Role {
        OWNER, ADMIN, MANAGER, STAFF, VIEWER
    }

    public enum Status {
        ACTIVE, INVITED, DISABLED
    }
}