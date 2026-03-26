package com.moneyops.security.team;

import com.moneyops.invites.EmailService;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.shared.exceptions.UnauthorizedException;
import com.moneyops.shared.exceptions.ValidationException;
import com.moneyops.users.entity.Invite;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.InviteRepository;
import com.moneyops.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class TeamSecurityCodeService {

    private final BusinessOrganizationRepository orgRepository;
    private final PasswordEncoder passwordEncoder;
    private final EmailService emailService;
    private final InviteRepository inviteRepository;
    private final UserRepository userRepository;

    public void assertTeamActionCodeConfigured(String orgId) {
        BusinessOrganization org = getOrgOrThrow(orgId);
        if (org.getTeamActionCodeHash() == null || org.getTeamActionCodeHash().isBlank()) {
            throw new ValidationException("Team security code is not configured for this workspace.");
        }
    }

    public void assertTeamActionCodeValid(String orgId, String rawTeamCode) {
        if (rawTeamCode == null || rawTeamCode.isBlank()) {
            throw new ValidationException("Team security code is required.");
        }

        BusinessOrganization org = getOrgOrThrow(orgId);
        String storedHash = org.getTeamActionCodeHash();
        if (storedHash == null || storedHash.isBlank()) {
            throw new ValidationException("Team security code is not configured for this workspace.");
        }

        if (!passwordEncoder.matches(rawTeamCode, storedHash)) {
            throw new ValidationException("Invalid team security code.");
        }
    }

    @Transactional
    public void setOrUpdateTeamActionCode(String orgId, String rawTeamCode, String oldRawTeamCode) {
        if (rawTeamCode == null || rawTeamCode.isBlank()) {
            throw new ValidationException("Team security code cannot be empty.");
        }

        // Basic sanity checks; keep it simple and allow a range for UX.
        if (rawTeamCode.length() < 4) {
            throw new ValidationException("Team security code must be at least 4 characters.");
        }

        BusinessOrganization org = getOrgOrThrow(orgId);
        String existingHash = org.getTeamActionCodeHash();
        boolean isUpdate = existingHash != null && !existingHash.isBlank();

        if (isUpdate) {
            if (oldRawTeamCode == null || oldRawTeamCode.isBlank()) {
                throw new ValidationException("Old team security code is required to update.");
            }
            if (!passwordEncoder.matches(oldRawTeamCode, existingHash)) {
                throw new ValidationException("Old team security code is incorrect.");
            }
        }

        org.setTeamActionCodeHash(passwordEncoder.encode(rawTeamCode));
        org.setUpdatedAt(LocalDateTime.now());
        
        try {
            orgRepository.save(org);
            log.info("Team security code {} for organization {}", isUpdate ? "updated" : "set", orgId);
            
            // If updating existing code, notify all accepted members via email
            if (isUpdate) {
                notifyMembersOfCodeChange(orgId, rawTeamCode, org.getLegalName());
            }
        } catch (Exception e) {
            log.error("Failed to save team security code for organization {}: {}", orgId, e.getMessage());
            throw new RuntimeException("Failed to save team security code: " + e.getMessage(), e);
        }
    }

    /**
     * Sends email notifications to all accepted members when the team security code is changed.
     * This ensures that members receive the updated code immediately after the owner changes it.
     */
    private void notifyMembersOfCodeChange(String orgId, String newTeamCode, String orgName) {
        try {
            // Get all accepted users in this organization
            List<User> acceptedMembers = userRepository.findAllByOrgIdAndStatusAndDeletedAtIsNull(
                    orgId, User.Status.ACTIVE
            );
            
            for (User member : acceptedMembers) {
                // Skip the owner from email notification (they already know)
                if (member.getRole() == User.Role.OWNER) {
                    continue;
                }
                
                try {
                    String subject = "Team Security Code Updated - " + (orgName != null ? orgName : "MoneyOps");
                    String htmlContent = buildSecurityCodeChangeEmailContent(newTeamCode, orgName);
                    sendSecurityCodeChangeEmail(member.getEmail(), subject, htmlContent);
                } catch (Exception e) {
                    log.error("Failed to send security code change notification to {}: {}", 
                              member.getEmail(), e.getMessage());
                    // Continue with other members even if one fails
                }
            }
        } catch (Exception e) {
            log.error("Failed to notify members of code change for organization {}: {}", 
                      orgId, e.getMessage());
            // Don't fail the entire operation if member notification fails
        }
    }

    private void sendSecurityCodeChangeEmail(String toEmail, String subject, String htmlContent) {
        try {
            log.info("Sending security code change notification to {}", toEmail);
            emailService.sendSecurityCodeChangeEmail(toEmail, subject, htmlContent);
        } catch (Exception e) {
            log.error("Error sending security code change email: {}", e.getMessage());
            throw e;
        }
    }

    private String buildSecurityCodeChangeEmailContent(String newTeamCode, String orgName) {
        return "<div style='font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;'>" +
               "  <h2 style='color: #4CBB17;'>Team Security Code Updated</h2>" +
               "  <p>The team security code for <strong>" + (orgName != null ? orgName : "your organization") + "</strong> has been changed.</p>" +
               "  <p>Your new team security code (required to create invoices/clients) is:</p>" +
               "  <div style='background-color: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center;'>" +
               "    <h1 style='margin: 10px 0; letter-spacing: 3px; color: #333;'><strong>" + newTeamCode + "</strong></h1>" +
               "  </div>" +
               "  <p style='color: #666; font-size: 14px;'>Please save this code in a secure location. You will need it to perform team actions.</p>" +
               "  <p style='margin-top: 20px; font-size: 12px; color: #999;'>For security, only team members can use this code to create clients and invoices.</p>" +
               "</div>";
    }

    private BusinessOrganization getOrgOrThrow(String orgId) {
        return orgRepository.findByIdAndDeletedAtIsNull(orgId)
                .orElseThrow(() -> new UnauthorizedException("Organization not found."));
    }
}
