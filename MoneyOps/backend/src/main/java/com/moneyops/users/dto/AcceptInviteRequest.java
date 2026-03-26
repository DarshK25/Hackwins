// src/main/java/com/moneyops/users/dto/AcceptInviteRequest.java
package com.moneyops.users.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class AcceptInviteRequest {
    private String token;
    private String name;
    private String phone;
}
