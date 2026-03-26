package com.moneyops.invites;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import jakarta.validation.Valid;
import com.moneyops.shared.utils.OrgContext;

import java.util.Map;

@RestController
@RequestMapping("/api/invites")
@RequiredArgsConstructor
public class InviteController {

    private final InviteService inviteService;

    @PostMapping
    public ResponseEntity<?> sendInvite(
            @Valid @RequestBody InviteRequest request,
            @RequestHeader("X-Org-Id") String orgId,
            @RequestHeader(value = "X-User-Id", required = false) String inviterUserIdHeader) {
            
        String inviterUserId = OrgContext.getUserId();
        if (inviterUserId == null || inviterUserId.isBlank()) {
            inviterUserId = inviterUserIdHeader;
        }

        String token = inviteService.createAndSendInvite(
                request.getEmail(),
                orgId,
                request.getRole(),
                request.getTeamActionCode(),
                inviterUserId
        );
        return ResponseEntity.ok(Map.of("message", "Invite sent successfully", "token", token));
    }

    @GetMapping("/{token}")
    public ResponseEntity<?> validateInvite(@PathVariable String token) {
        TeamInvite invite = inviteService.validateToken(token);
        return ResponseEntity.ok(invite);
    }

    @PostMapping("/accept/{token}")
    public ResponseEntity<?> acceptInvite(
            @PathVariable String token,
            @RequestHeader("X-User-Id") String userId) {
            
        inviteService.acceptInvite(token, userId);
        return ResponseEntity.ok(Map.of("message", "Invite accepted successfully"));
    }
}
