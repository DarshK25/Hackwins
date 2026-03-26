package com.moneyops.organizations.controller;

import com.moneyops.organizations.dto.TeamSecurityCodeUpdateRequest;
import com.moneyops.organizations.dto.TeamSecurityCodeValidationRequest;
import com.moneyops.security.team.TeamActionAuthorizationService;
import com.moneyops.security.team.TeamSecurityCodeService;
import com.moneyops.shared.dto.ApiResponse;
import com.moneyops.shared.utils.OrgContext;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequiredArgsConstructor
public class TeamSecurityCodeController {

    private final TeamSecurityCodeService teamSecurityCodeService;
    private final TeamActionAuthorizationService teamActionAuthorizationService;

    @PutMapping("/api/org/{orgId}/team-security-code")
    public ResponseEntity<ApiResponse<Map<String, String>>> setTeamSecurityCode(
            @PathVariable String orgId,
            @Valid @RequestBody TeamSecurityCodeUpdateRequest request,
            @RequestHeader(value = "X-User-Id", required = false) String userIdHeader) {

        String userId = OrgContext.getUserId();
        if (userId == null || userId.isBlank()) {
            userId = userIdHeader;
        }

        teamActionAuthorizationService.assertOwnerCanSetTeamActionCode(orgId, userId);
        teamSecurityCodeService.setOrUpdateTeamActionCode(
                orgId,
                request.getTeamActionCode(),
                request.getOldTeamActionCode()
        );

        return ResponseEntity.ok(
                ApiResponse.success(Map.of("message", "Team security code updated successfully"))
        );
    }

    @PostMapping("/api/org/{orgId}/team-security-code/validate")
    public ResponseEntity<ApiResponse<Map<String, Object>>> validateTeamSecurityCode(
            @PathVariable String orgId,
            @Valid @RequestBody TeamSecurityCodeValidationRequest request,
            @RequestHeader(value = "X-User-Id", required = false) String userIdHeader) {

        String userId = OrgContext.getUserId();
        if (userId == null || userId.isBlank()) {
            userId = userIdHeader;
        }

        teamActionAuthorizationService.assertUserCanCreateSensitiveAction(
                orgId,
                userId,
                request.getTeamActionCode()
        );

        return ResponseEntity.ok(
                ApiResponse.success(Map.of(
                        "valid", true,
                        "message", "Team security code validated successfully"
                ))
        );
    }
}

