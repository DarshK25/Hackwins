// src/main/java/com/ledgertalk/auth/dto/LoginRequest.java
package com.ledgertalk.auth.dto;

import lombok.Data;

@Data
public class LoginRequest {
    private String email;
    private String password;
}