// src/main/java/com/moneyops/auth/dto/OAuthUserInfo.java
package com.moneyops.auth.dto;

import lombok.Data;

@Data
public class OAuthUserInfo {
    private String id;
    private String email;
    private String name;
    private String picture;
}