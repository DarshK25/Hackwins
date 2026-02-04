// src/main/java/com/moneyops/users/dto/AcceptInviteRequest.java
package com.moneyops.users.dto;

import lombok.Data;

@Data
public class AcceptInviteRequest {
    private String token;
    private String name;
    private String phone;
    private String password;
}