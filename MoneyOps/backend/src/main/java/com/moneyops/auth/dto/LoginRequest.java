// src/main/java/com/moneyops/auth/dto/LoginRequest.java
package com.moneyops.auth.dto;

import lombok.Data;

@Data
public class LoginRequest {
    private String email;
    private String password;
}