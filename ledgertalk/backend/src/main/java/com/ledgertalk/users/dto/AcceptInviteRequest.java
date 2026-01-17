// src/main/java/com/ledgertalk/users/dto/AcceptInviteRequest.java
package com.ledgertalk.users.dto;

import lombok.Data;

@Data
public class AcceptInviteRequest {
    private String token;
    private String name;
    private String phone;
    private String password;
}