package com.moneyops.teams.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TeamMemberDTO {
    private String id;
    private String name;
    private String email;
    private String role;
    private String status;
    private LocalDateTime joinedAt;
    private LocalDateTime lastLoginAt;
    private boolean pendingInvite;
}
