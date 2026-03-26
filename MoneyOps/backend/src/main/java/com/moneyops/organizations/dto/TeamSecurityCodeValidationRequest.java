package com.moneyops.organizations.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class TeamSecurityCodeValidationRequest {

    @NotBlank
    private String teamActionCode;
}
