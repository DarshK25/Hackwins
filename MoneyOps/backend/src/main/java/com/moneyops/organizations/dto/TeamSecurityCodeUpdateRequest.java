package com.moneyops.organizations.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class TeamSecurityCodeUpdateRequest {

    /**
     * Raw team security code. It will be BCrypt-hashed server-side.
     */
    @NotBlank
    private String teamActionCode;

    /**
     * Required only when a code already exists (to update securely).
     */
    private String oldTeamActionCode;
}

