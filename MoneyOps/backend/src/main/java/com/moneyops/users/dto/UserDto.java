// src/main/java/com/moneyops/users/dto/UserDto.java
package com.moneyops.users.dto;

import lombok.Data;
import java.time.LocalDateTime;
import java.util.UUID;

@Data
public class UserDto {
    private UUID id;
    private String name;
    private String email;
    private String phone;
    private String role;
    private String status;
    private LocalDateTime lastLoginAt;
}