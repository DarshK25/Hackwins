package com.moneyops.teams.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class InviteDTO {
    private String email;
    private String role;
    private String teamActionCode;
    private String token;
    private String status;
    private Instant expiresAt;
}
