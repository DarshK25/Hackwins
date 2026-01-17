// src/main/java/com/ledgertalk/users/entity/User.java
package com.ledgertalk.users.entity;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "users")
@Data
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false)
    private UUID orgId;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false, unique = true)
    private String email;

    private String phone;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Role role = Role.STAFF;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Status status = Status.ACTIVE;

    @Column(nullable = false)
    private String passwordHash;

    private LocalDateTime lastLoginAt;

    @Column(nullable = false)
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(nullable = false)
    private LocalDateTime updatedAt = LocalDateTime.now();

    @Column(nullable = false)
    private UUID createdBy;

    @Column(nullable = false)
    private UUID updatedBy;

    public enum Role {
        OWNER, ADMIN, MANAGER, STAFF, VIEWER
    }

    public enum Status {
        ACTIVE, INVITED, DISABLED
    }
}