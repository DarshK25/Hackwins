// src/main/java/com/ledgertalk/users/dto/InviteDto.java
package com.ledgertalk.users.dto;

import lombok.Data;
import java.time.LocalDateTime;
import java.util.UUID;

@Data
public class InviteDto {
    private UUID id;
    private String email;
    private String role;
    private LocalDateTime expiresAt;
    private String status;
}