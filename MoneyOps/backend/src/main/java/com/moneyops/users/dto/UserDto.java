// src/main/java/com/moneyops/users/dto/UserDto.java
package com.moneyops.users.dto;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class UserDto {
    private String id;
    private String name;
    private String email;
    private String phone;
    private String role;
    private String status;
    private LocalDateTime lastLoginAt;
}