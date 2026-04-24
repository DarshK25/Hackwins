package com.moneyops.teams.controller;

import com.moneyops.organizations.dto.BusinessOrganizationDto;
import com.moneyops.shared.dto.ApiResponse;
import com.moneyops.teams.dto.InviteDTO;
import com.moneyops.teams.dto.TeamMemberDTO;
import com.moneyops.teams.service.TeamService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/teams")
@RequiredArgsConstructor
public class TeamController {

    private final TeamService teamService;

    @GetMapping("/members")
    public ResponseEntity<ApiResponse<List<TeamMemberDTO>>> getMembers(
            @RequestParam(required = false) String orgId
    ) {
        return ResponseEntity.ok(ApiResponse.success(teamService.getMembers(orgId)));
    }

    @GetMapping("/organization")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> getOrganization() {
        return ResponseEntity.ok(ApiResponse.success(teamService.getOrganization()));
    }

    @PostMapping("/invite")
    public ResponseEntity<ApiResponse<InviteDTO>> inviteMember(@RequestBody InviteDTO inviteDTO) {
        return ResponseEntity.ok(ApiResponse.success("Invite sent successfully", teamService.inviteMember(inviteDTO)));
    }

    @PutMapping("/members/{userId}/role")
    public ResponseEntity<ApiResponse<TeamMemberDTO>> updateMemberRole(
            @PathVariable String userId,
            @RequestBody Map<String, String> payload
    ) {
        return ResponseEntity.ok(ApiResponse.success(
                "Team role updated successfully",
                teamService.updateMemberRole(userId, payload.get("role"))
        ));
    }

    @DeleteMapping("/members/{userId}")
    public ResponseEntity<ApiResponse<Void>> removeMember(@PathVariable String userId) {
        teamService.removeMember(userId);
        return ResponseEntity.ok(ApiResponse.success("Team member removed successfully", null));
    }
}
