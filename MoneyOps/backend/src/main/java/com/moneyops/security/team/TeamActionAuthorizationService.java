package com.moneyops.security.team;

import com.moneyops.shared.exceptions.ForbiddenException;
import com.moneyops.shared.exceptions.UnauthorizedException;
import com.moneyops.shared.exceptions.ValidationException;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class TeamActionAuthorizationService {

    private final UserRepository userRepository;
    private final TeamSecurityCodeService teamSecurityCodeService;

    public CreatorMetadata assertUserCanCreateSensitiveAction(String orgId, String userId, String rawTeamCode) {
        if (orgId == null || orgId.isBlank()) {
            throw new UnauthorizedException("Organization context missing.");
        }
        if (userId == null || userId.isBlank()) {
            throw new UnauthorizedException("User context missing.");
        }

        User user = userRepository.findByIdAndOrgIdAndDeletedAtIsNull(userId, orgId)
                .orElseThrow(() -> new UnauthorizedException("User not part of this organization."));

        if (user.getStatus() != User.Status.ACTIVE) {
            throw new UnauthorizedException("Only active team members can perform this action.");
        }

        // Your system's non-owner team role is currently represented as STAFF.
        if (!(user.getRole() == User.Role.OWNER || user.getRole() == User.Role.STAFF)) {
            throw new ForbiddenException("You are not authorized to perform this action.");
        }

        // Final enforcement: backend verifies the PIN.
        teamSecurityCodeService.assertTeamActionCodeValid(orgId, rawTeamCode);

        return new CreatorMetadata(user.getId(), user.getEmail(), user.getRole().name());
    }

    public void assertOwnerCanSetTeamActionCode(String orgId, String userId) {
        if (orgId == null || orgId.isBlank() || userId == null || userId.isBlank()) {
            throw new UnauthorizedException("Organization or user context missing.");
        }

        User user = userRepository.findByIdAndOrgIdAndDeletedAtIsNull(userId, orgId)
                .orElseThrow(() -> new UnauthorizedException("User not part of this organization."));

        if (user.getStatus() != User.Status.ACTIVE) {
            throw new UnauthorizedException("Only active owners can update the security code.");
        }

        if (user.getRole() != User.Role.OWNER) {
            throw new ForbiddenException("Only the owner can update the team security code.");
        }
    }

    public record CreatorMetadata(String userId, String email, String role) {
        public CreatorMetadata {
            if (userId == null || userId.isBlank()) throw new ValidationException("Creator userId missing.");
        }
    }
}

