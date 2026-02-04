// src/main/java/com/moneyops/users/dto/CreateInviteRequest.java
package com.moneyops.users.dto;

import lombok.Data;

@Data
public class CreateInviteRequest {
    private String email;
    private String role;
}