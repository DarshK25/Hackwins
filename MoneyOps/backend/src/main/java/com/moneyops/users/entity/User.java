package com.moneyops.users.entity;

import lombok.Data;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;
import java.util.UUID;

import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;
import jakarta.annotation.PostConstruct;

import java.time.LocalDateTime;
import java.util.UUID;

@Document(collection = "users")
@Data
public class User {

    @Id
    private String id;

    @Indexed
    private String orgId;      // 🔗 Tenant isolation
    
    private String name;

    @Indexed(unique = true)
    private String email;

    private String phone;
    private Role role = Role.STAFF;
    private Status status = Status.ACTIVE;
    private String passwordHash;

    // Clerk user ID — stored so we can look up a user by their Clerk token
    @Indexed(unique = true)
    private String clerkId;

    private boolean onboardingComplete = false;

    private LocalDateTime lastLoginAt;
    
    @CreatedDate
    private LocalDateTime createdAt;
    
    @LastModifiedDate
    private LocalDateTime updatedAt;
    
    @CreatedBy
    private String createdBy;
    
    @LastModifiedBy
    private String updatedBy;
    
    private LocalDateTime deletedAt;

    @PostConstruct
    public void generateId() {
        if (this.id == null) {
            this.id = UUID.randomUUID().toString();
        }
    }

    public enum Role {
        OWNER, ADMIN, MANAGER, STAFF, VIEWER
    }

    public enum Status {
        ACTIVE, INVITED, DISABLED
    }
}