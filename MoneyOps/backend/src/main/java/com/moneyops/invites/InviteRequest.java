package com.moneyops.invites;

import lombok.Data;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

@Data
public class InviteRequest {
    @NotBlank
    @Email
    private String email;
    
    @NotBlank
    private String role;

    @NotBlank
    private String teamActionCode;
}
