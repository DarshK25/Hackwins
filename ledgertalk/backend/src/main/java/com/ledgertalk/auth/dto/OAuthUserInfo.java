// src/main/java/com/ledgertalk/auth/dto/OAuthUserInfo.java
package com.ledgertalk.auth.dto;

import lombok.Data;

@Data
public class OAuthUserInfo {
    private String id;
    private String email;
    private String name;
    private String picture;
}