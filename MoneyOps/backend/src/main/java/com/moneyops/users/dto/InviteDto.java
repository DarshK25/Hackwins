// src/main/java/com/moneyops/users/dto/InviteDto.java
package com.moneyops.users.dto;

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