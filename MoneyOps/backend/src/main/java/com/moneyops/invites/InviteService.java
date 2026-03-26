package com.moneyops.invites;

import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.security.team.TeamActionAuthorizationService;
import com.moneyops.security.team.TeamSecurityCodeService;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class InviteService {

    private final TeamInviteRepository inviteRepository;
    private final EmailService emailService;
    private final UserRepository userRepository;
    private final BusinessOrganizationRepository orgRepository;
    private final TeamActionAuthorizationService teamActionAuthorizationService;
    private final TeamSecurityCodeService teamSecurityCodeService;

    @Transactional
    public String createAndSendInvite(String email, String orgId, String role, String teamActionCode, String inviterUserId) {
        // Only the owner can send invites (and the inviter must provide a valid team PIN).
        teamActionAuthorizationService.assertOwnerCanSetTeamActionCode(orgId, inviterUserId);
        teamSecurityCodeService.assertTeamActionCodeValid(orgId, teamActionCode);

        BusinessOrganization org = orgRepository.findByIdAndDeletedAtIsNull(orgId)
                .orElseThrow(() -> new RuntimeException("Organization not found"));
        String orgName = (org.getTradingName() != null && !org.getTradingName().isBlank())
                ? org.getTradingName()
                : org.getLegalName();

        String normalizedRole = role != null ? role.toUpperCase() : "STAFF";

        Optional<TeamInvite> existing = inviteRepository.findByEmailAndOrgId(email, orgId);
        if (existing.isPresent() && "PENDING".equals(existing.get().getStatus())) {
            TeamInvite invite = existing.get();
            invite.setToken(UUID.randomUUID().toString());
            invite.setExpiresAt(Instant.now().plus(24, ChronoUnit.HOURS));
            inviteRepository.save(invite);
            emailService.sendInviteEmail(email, invite.getToken(), orgName, invite.getRole(), teamActionCode);
            return invite.getToken();
        }

        String token = UUID.randomUUID().toString();
        
        TeamInvite invite = TeamInvite.builder()
                .email(email)
                .orgId(orgId)
                .role(normalizedRole)
                .token(token)
                .status("PENDING")
                .createdAt(Instant.now())
                .expiresAt(Instant.now().plus(24, ChronoUnit.HOURS))
                .build();
                
        inviteRepository.save(invite);
        
        emailService.sendInviteEmail(email, token, orgName, invite.getRole(), teamActionCode);
        
        return token;
    }

    public TeamInvite validateToken(String token) {
        TeamInvite invite = inviteRepository.findByToken(token)
                .orElseThrow(() -> new RuntimeException("Invalid or expired invite token"));
                
        if (!"PENDING".equals(invite.getStatus())) {
            throw new RuntimeException("Invite has already been accepted or expired");
        }
        
        if (invite.getExpiresAt().isBefore(Instant.now())) {
            invite.setStatus("EXPIRED");
            inviteRepository.save(invite);
            throw new RuntimeException("Invite has expired");
        }
        
        return invite;
    }

    @Transactional
    public void acceptInvite(String token, String userId) {
        TeamInvite invite = validateToken(token);
        
        User user = userRepository.findByIdAndDeletedAtIsNull(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));
                
        user.setOrgId(invite.getOrgId());
        try {
            user.setRole(User.Role.valueOf(invite.getRole()));
        } catch (Exception e) {
            user.setRole(User.Role.STAFF);
        }
        user.setStatus(User.Status.ACTIVE);
        userRepository.save(user);
        
        invite.setStatus("ACCEPTED");
        inviteRepository.save(invite);
        
        log.info("User {} accepted invite to org {}", userId, invite.getOrgId());
    }
}
