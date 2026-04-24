package com.moneyops.teams.service;

import com.moneyops.invites.EmailService;
import com.moneyops.invites.TeamInvite;
import com.moneyops.invites.TeamInviteRepository;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.shared.exceptions.NotFoundException;
import com.moneyops.teams.dto.InviteDTO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Locale;
import java.util.UUID;

@Service("teamInviteService")
@RequiredArgsConstructor
public class InviteService {

    private final TeamInviteRepository teamInviteRepository;
    private final BusinessOrganizationRepository businessOrganizationRepository;
    private final EmailService emailService;

    @Transactional
    public InviteDTO createInvite(String orgId, String invitedByUserId, String email, String role, String teamActionCode) {
        BusinessOrganization organization = businessOrganizationRepository.findByIdAndDeletedAtIsNull(orgId)
                .orElseThrow(() -> new NotFoundException("Organization", orgId));

        String normalizedEmail = email.trim().toLowerCase(Locale.ROOT);
        String normalizedRole = role.trim().toUpperCase(Locale.ROOT);
        Instant expiresAt = Instant.now().plus(7, ChronoUnit.DAYS);

        TeamInvite invite = teamInviteRepository.findByEmailAndOrgId(normalizedEmail, orgId)
                .orElseGet(TeamInvite::new);

        invite.setEmail(normalizedEmail);
        invite.setOrgId(orgId);
        invite.setInvitedByUserId(invitedByUserId);
        invite.setRole(normalizedRole);
        invite.setToken(UUID.randomUUID().toString());
        invite.setStatus("PENDING");
        invite.setCreatedAt(Instant.now());
        invite.setExpiresAt(expiresAt);

        TeamInvite savedInvite = teamInviteRepository.save(invite);

        String organizationName = organization.getTradingName() != null && !organization.getTradingName().isBlank()
                ? organization.getTradingName()
                : organization.getLegalName();
        emailService.sendInviteEmail(normalizedEmail, savedInvite.getToken(), organizationName, normalizedRole, teamActionCode);

        return InviteDTO.builder()
                .email(savedInvite.getEmail())
                .role(savedInvite.getRole())
                .token(savedInvite.getToken())
                .status(savedInvite.getStatus())
                .expiresAt(savedInvite.getExpiresAt())
                .build();
    }
}
