package com.moneyops.teams.service;

import com.moneyops.invites.TeamInvite;
import com.moneyops.invites.TeamInviteRepository;
import com.moneyops.organizations.dto.BusinessOrganizationDto;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.mapper.OrganizationMapper;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.security.team.TeamSecurityCodeService;
import com.moneyops.shared.exceptions.ForbiddenException;
import com.moneyops.shared.exceptions.NotFoundException;
import com.moneyops.shared.exceptions.UnauthorizedException;
import com.moneyops.shared.exceptions.ValidationException;
import com.moneyops.shared.utils.OrgContext;
import com.moneyops.teams.dto.InviteDTO;
import com.moneyops.teams.dto.TeamMemberDTO;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Set;

@Service
@RequiredArgsConstructor
public class TeamService {

    private static final Set<String> MANAGEABLE_ROLES = Set.of("ADMIN", "MANAGER", "STAFF", "VIEWER");

    private final UserRepository userRepository;
    private final BusinessOrganizationRepository businessOrganizationRepository;
    private final OrganizationMapper organizationMapper;
    private final InviteService inviteService;
    private final TeamInviteRepository teamInviteRepository;
    private final TeamSecurityCodeService teamSecurityCodeService;

    public List<TeamMemberDTO> getMembers(String fallbackOrgId) {
        User currentUser = resolveCurrentUser();
        String orgId = resolveOrgId(currentUser, fallbackOrgId);

        List<TeamMemberDTO> members = new ArrayList<>();

        userRepository.findAllByOrgIdAndDeletedAtIsNull(orgId).stream()
                .map(this::toTeamMemberDto)
                .forEach(members::add);

        for (TeamInvite invite : teamInviteRepository.findAllByOrgIdOrderByCreatedAtDesc(orgId)) {
            if (!"PENDING".equalsIgnoreCase(invite.getStatus())) {
                continue;
            }

            if (invite.getExpiresAt() != null && invite.getExpiresAt().isBefore(Instant.now())) {
                invite.setStatus("EXPIRED");
                teamInviteRepository.save(invite);
                continue;
            }

            members.add(TeamMemberDTO.builder()
                    .id("invite:" + invite.getId())
                    .name("Pending invite")
                    .email(invite.getEmail())
                    .role(invite.getRole())
                    .status("PENDING")
                    .joinedAt(toLocalDateTime(invite.getCreatedAt()))
                    .pendingInvite(true)
                    .build());
        }

        members.sort(Comparator
                .comparing(TeamMemberDTO::isPendingInvite)
                .thenComparing(TeamMemberDTO::getJoinedAt, Comparator.nullsLast(Comparator.reverseOrder())));

        return members;
    }

    public BusinessOrganizationDto getOrganization() {
        User currentUser = resolveCurrentUser();
        String orgId = resolveOrgId(currentUser, null);
        BusinessOrganization organization = businessOrganizationRepository.findByIdAndDeletedAtIsNull(orgId)
                .orElseThrow(() -> new NotFoundException("Organization", orgId));
        return organizationMapper.toDto(organization);
    }

    public InviteDTO inviteMember(InviteDTO request) {
        User currentUser = resolveCurrentUser();
        String orgId = resolveOrgId(currentUser, null);
        assertCanManageMembers(currentUser);

        if (request == null) {
            throw new ValidationException(List.of("Invite payload is required"));
        }
        if (request.getEmail() == null || request.getEmail().isBlank()) {
            throw new ValidationException(List.of("Invite email is required"));
        }
        if (request.getRole() == null || request.getRole().isBlank()) {
            throw new ValidationException(List.of("Invite role is required"));
        }

        String normalizedRole = request.getRole().trim().toUpperCase(Locale.ROOT);
        validateRoleForManager(currentUser, normalizedRole);
        teamSecurityCodeService.assertTeamActionCodeValid(orgId, request.getTeamActionCode());

        String normalizedEmail = request.getEmail().trim();
        boolean existingMember = userRepository.findAllByOrgIdAndDeletedAtIsNull(orgId).stream()
                .anyMatch(user -> user.getEmail() != null && user.getEmail().equalsIgnoreCase(normalizedEmail));

        if (existingMember) {
            throw new ValidationException("A team member with this email already exists.");
        }

        return inviteService.createInvite(orgId, currentUser.getId(), normalizedEmail, normalizedRole, request.getTeamActionCode());
    }

    @Transactional
    public TeamMemberDTO updateMemberRole(String memberId, String requestedRole) {
        User currentUser = resolveCurrentUser();
        String orgId = resolveOrgId(currentUser, null);
        assertCanManageMembers(currentUser);

        if (requestedRole == null || requestedRole.isBlank()) {
            throw new ValidationException(List.of("Role is required"));
        }

        User targetUser = userRepository.findByIdAndOrgIdAndDeletedAtIsNull(memberId, orgId)
                .orElseThrow(() -> new NotFoundException("User", memberId));

        if (currentUser.getId().equals(targetUser.getId())) {
            throw new ValidationException("You cannot change your own role from this screen.");
        }
        if (targetUser.getRole() == User.Role.OWNER) {
            throw new ForbiddenException("The owner role cannot be changed here.");
        }

        String normalizedRole = requestedRole.trim().toUpperCase(Locale.ROOT);
        validateRoleForManager(currentUser, normalizedRole);

        targetUser.setRole(User.Role.valueOf(normalizedRole));
        targetUser.setUpdatedBy(currentUser.getId());
        userRepository.save(targetUser);

        return toTeamMemberDto(targetUser);
    }

    @Transactional
    public void removeMember(String memberId) {
        User currentUser = resolveCurrentUser();
        String orgId = resolveOrgId(currentUser, null);
        assertCanManageMembers(currentUser);

        User targetUser = userRepository.findByIdAndOrgIdAndDeletedAtIsNull(memberId, orgId)
                .orElseThrow(() -> new NotFoundException("User", memberId));

        if (currentUser.getId().equals(targetUser.getId())) {
            throw new ValidationException("You cannot remove yourself from the organization.");
        }
        if (targetUser.getRole() == User.Role.OWNER) {
            throw new ForbiddenException("The owner cannot be removed from this screen.");
        }

        targetUser.setStatus(User.Status.DISABLED);
        targetUser.setDeletedAt(LocalDateTime.now());
        targetUser.setUpdatedBy(currentUser.getId());
        userRepository.save(targetUser);
    }

    private User resolveCurrentUser() {
        String contextUserId = OrgContext.getUserId();
        if (contextUserId == null || contextUserId.isBlank()) {
            throw new UnauthorizedException("Missing user context");
        }

        return userRepository.findByIdAndDeletedAtIsNull(contextUserId)
                .or(() -> userRepository.findByClerkIdAndDeletedAtIsNull(contextUserId))
                .orElseThrow(() -> new UnauthorizedException("Authenticated user could not be resolved"));
    }

    private String resolveOrgId(User currentUser, String fallbackOrgId) {
        String contextOrgId = trimToNull(OrgContext.getOrgId());
        if (contextOrgId != null) {
            assertOrgAccess(currentUser, contextOrgId);
            return contextOrgId;
        }

        String userOrgId = trimToNull(currentUser.getOrgId());
        if (userOrgId != null) {
            return userOrgId;
        }

        String requestedOrgId = trimToNull(fallbackOrgId);
        if (requestedOrgId != null) {
            assertOrgAccess(currentUser, requestedOrgId);
            return requestedOrgId;
        }

        throw new UnauthorizedException("Missing organization context");
    }

    private void assertOrgAccess(User currentUser, String orgId) {
        if (orgId.equals(currentUser.getOrgId())) {
            return;
        }

        businessOrganizationRepository.findByIdAndCreatedByAndDeletedAtIsNull(orgId, currentUser.getId())
                .orElseThrow(() -> new ForbiddenException("You do not have access to this organization."));
    }

    private void assertCanManageMembers(User currentUser) {
        if (currentUser.getStatus() != User.Status.ACTIVE) {
            throw new UnauthorizedException("Only active members can manage the team.");
        }
        if (currentUser.getRole() != User.Role.OWNER && currentUser.getRole() != User.Role.ADMIN) {
            throw new ForbiddenException("Only owners and admins can manage the team.");
        }
    }

    private void validateRoleForManager(User currentUser, String requestedRole) {
        if (!MANAGEABLE_ROLES.contains(requestedRole)) {
            throw new ValidationException("Unsupported team role: " + requestedRole);
        }
        if (currentUser.getRole() == User.Role.ADMIN && "ADMIN".equals(requestedRole)) {
            throw new ForbiddenException("Admins cannot grant the admin role.");
        }
    }

    private TeamMemberDTO toTeamMemberDto(User user) {
        return TeamMemberDTO.builder()
                .id(user.getId())
                .name(user.getName())
                .email(user.getEmail())
                .role(user.getRole().name())
                .status(user.getStatus().name())
                .joinedAt(user.getCreatedAt())
                .lastLoginAt(user.getLastLoginAt())
                .pendingInvite(false)
                .build();
    }

    private LocalDateTime toLocalDateTime(Instant instant) {
        return instant == null ? null : LocalDateTime.ofInstant(instant, ZoneOffset.UTC);
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }

        String trimmed = value.trim();
        return trimmed.isBlank() ? null : trimmed;
    }
}
