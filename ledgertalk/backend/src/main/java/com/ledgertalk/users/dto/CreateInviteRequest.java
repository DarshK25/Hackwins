// src/main/java/com/ledgertalk/users/dto/CreateInviteRequest.java
package com.ledgertalk.users.dto;

import lombok.Data;

@Data
public class CreateInviteRequest {
    private String email;
    private String role;
}