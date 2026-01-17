// src/main/java/com/ledgertalk/auth/dto/RegisterRequest.java
package com.ledgertalk.auth.dto;

import lombok.Data;

@Data
public class RegisterRequest {
    private String name;
    private String email;
    private String password;
    private String orgName;
}