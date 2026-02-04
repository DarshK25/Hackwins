// src/main/java/com/moneyops/auth/dto/RegisterRequest.java
package com.moneyops.auth.dto;

import lombok.Data;

@Data
public class RegisterRequest {
    private String name;
    private String email;
    private String password;
    private String orgName;
}