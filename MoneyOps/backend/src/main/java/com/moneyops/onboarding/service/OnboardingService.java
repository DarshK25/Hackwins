package com.moneyops.onboarding.service;

import com.moneyops.onboarding.dto.OnboardingRequest;
import com.moneyops.onboarding.dto.OnboardingStatusResponse;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.users.entity.Invite;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.InviteRepository;
import com.moneyops.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

@Service
@RequiredArgsConstructor
@Slf4j
public class OnboardingService {

    private final UserRepository userRepository;
    private final BusinessOrganizationRepository orgRepository;
    private final InviteRepository inviteRepository;
    private final PasswordEncoder passwordEncoder;

    public OnboardingStatusResponse getStatus(String clerkId) {
        return getStatus(clerkId, null);
    }

    public OnboardingStatusResponse getStatus(String clerkId, String email) {
        Optional<User> userOpt = findUserByIdentity(clerkId, email);

        if (userOpt.isEmpty()) {
            return newUserResponse("New user - onboarding required");
        }

        User user = userOpt.get();
        String orgId = resolveActiveOrganizationId(user);

        if (orgId == null) {
            if (isOrphanedDeletedAccount(user)) {
                log.warn(
                        "User has no active workspace during onboarding status check. Preserving identity for recovery. clerkId={}, userId={}, staleOrgId={}",
                        clerkId,
                        user.getId(),
                        user.getOrgId()
                );
                user.setOrgId(null);
                user.setOnboardingComplete(false);
                userRepository.save(user);

                return new OnboardingStatusResponse(
                        false,
                        user.getId(),
                        null,
                        "Previous workspace unavailable - onboarding required"
                );
            }

            return new OnboardingStatusResponse(
                    false,
                    user.getId(),
                    null,
                    "Onboarding incomplete"
            );
        }

        if (!orgId.equals(user.getOrgId()) || !user.isOnboardingComplete()) {
            user.setOrgId(orgId);
            user.setOnboardingComplete(true);
            userRepository.save(user);
        }

        return new OnboardingStatusResponse(
                true,
                user.getId(),
                orgId,
                "Onboarding complete"
        );
    }

    public OnboardingStatusResponse createBusiness(OnboardingRequest req) {
        log.info("Creating business for clerkId={}, legalName={}", req.getClerkId(), req.getLegalName());

        User user = getOrCreateUser(req);
        String existingOrgId = resolveActiveOrganizationId(user);
        if (existingOrgId != null) {
            if (!existingOrgId.equals(user.getOrgId()) || !user.isOnboardingComplete()) {
                user.setOrgId(existingOrgId);
                user.setOnboardingComplete(true);
                userRepository.save(user);
            }

            return new OnboardingStatusResponse(
                    true,
                    user.getId(),
                    existingOrgId,
                    "Business already exists for this account"
            );
        }

        BusinessOrganization org = new BusinessOrganization();
        org.setLegalName(req.getLegalName());
        org.setTradingName(req.getTradingName());
        org.setBusinessType(req.getBusinessType());
        org.setIndustry(req.getIndustry());
        if (req.getRegistrationDate() != null && !req.getRegistrationDate().isEmpty()) {
            org.setRegistrationDate(java.time.LocalDate.parse(req.getRegistrationDate()));
        }
        org.setAnnualTurnover(req.getAnnualTurnover());
        org.setPrimaryEmail(req.getPrimaryEmail());
        org.setPrimaryPhone(req.getPrimaryPhone());
        org.setWebsite(req.getWebsite());
        org.setEmployeeCount(req.getNumberOfEmployees());
        org.setRegisteredAddress(req.getRegisteredAddress());

        org.setPanNumber(req.getPanNumber());
        org.setStateOfRegistration(req.getStateOfRegistration());
        org.setGstRegistered(Boolean.TRUE.equals(req.getGstRegistered()));
        org.setGstin(req.getGstin());
        org.setGstFilingFrequency(req.getGstFilingFrequency());
        org.setTanNumber(req.getTanNumber());
        org.setCin(req.getCin());
        org.setLlpin(req.getLlpin());
        org.setMsmeNumber(req.getMsmeNumber());
        org.setIecCode(req.getIecCode());
        org.setProfessionalTaxReg(req.getProfessionalTaxReg());

        org.setPrimaryActivity(req.getPrimaryActivity());
        org.setTargetMarket(req.getTargetMarket());
        org.setKeyProducts(req.getKeyProducts());
        org.setCurrentChallenges(req.getCurrentChallenges());
        org.setAccountingMethod(req.getAccountingMethod());
        org.setFyStartMonth(req.getFyStartMonth() != null ? req.getFyStartMonth() : 4);
        org.setPreferredLanguage(req.getPreferredLanguage() != null ? req.getPreferredLanguage() : "en");

        if (req.getTeamActionCode() != null && !req.getTeamActionCode().trim().isEmpty()) {
            org.setTeamActionCodeHash(passwordEncoder.encode(req.getTeamActionCode()));
            log.info("Team security code set for organization during onboarding");
        }

        org.setCreatedBy(user.getId());

        BusinessOrganization savedOrg = orgRepository.save(org);
        user.setOrgId(savedOrg.getId());
        user.setOnboardingComplete(true);
        user.setRole(User.Role.OWNER);
        userRepository.save(user);

        return new OnboardingStatusResponse(
                true,
                user.getId(),
                savedOrg.getId(),
                "Business created successfully"
        );
    }

    public Map<String, Object> verifyInvite(String code) {
        Invite invite = inviteRepository.findByTokenAndDeletedAtIsNull(code)
                .orElseThrow(() -> new RuntimeException("Invalid or expired invite code"));

        if (invite.getStatus() != Invite.InviteStatus.PENDING) {
            throw new RuntimeException("This invite code has already been used");
        }

        if (invite.getExpiresAt().isBefore(LocalDateTime.now())) {
            throw new RuntimeException("This invite code has expired");
        }

        BusinessOrganization org = orgRepository.findByIdAndDeletedAtIsNull(invite.getOrgId())
                .orElseThrow(() -> new RuntimeException("Organisation no longer exists"));

        return Map.of(
                "valid", true,
                "businessName", org.getLegalName(),
                "role", invite.getRole()
        );
    }

    public OnboardingStatusResponse joinBusiness(OnboardingRequest req) {
        log.info("User clerkId={} joining via code={}", req.getClerkId(), req.getInviteCode());

        Invite invite = inviteRepository.findByTokenAndDeletedAtIsNull(req.getInviteCode())
                .orElseThrow(() -> new RuntimeException("Invalid invite code"));

        if (invite.getStatus() != Invite.InviteStatus.PENDING) {
            throw new RuntimeException("Invite code already used");
        }

        BusinessOrganization org = orgRepository.findByIdAndDeletedAtIsNull(invite.getOrgId())
                .orElseThrow(() -> new RuntimeException("Organisation not found"));

        User user = getOrCreateUser(req);
        user.setOrgId(org.getId());
        user.setOnboardingComplete(true);
        user.setRole(invite.getRole());
        userRepository.save(user);

        invite.setStatus(Invite.InviteStatus.ACCEPTED);
        invite.setUpdatedAt(LocalDateTime.now());
        inviteRepository.save(invite);

        return new OnboardingStatusResponse(
                true,
                user.getId(),
                org.getId(),
                "Joined organisation successfully"
        );
    }

    private String resolveActiveOrganizationId(User user) {
        String orgId = user.getOrgId();

        if (orgId != null && orgRepository.findByIdAndDeletedAtIsNull(orgId).isPresent()) {
            return orgId;
        }

        if (orgId != null) {
            log.warn("User {} references missing organization {}", user.getEmail(), orgId);
        } else {
            log.info("User {} has no orgId, checking for created organizations", user.getEmail());
        }

        var createdOrgs = orgRepository.findAllByCreatedByAndDeletedAtIsNull(user.getId());
        if (createdOrgs.isEmpty()) {
            return null;
        }

        String healedOrgId = createdOrgs.get(0).getId();
        log.info("Healed user {} with orgId {}", user.getEmail(), healedOrgId);
        return healedOrgId;
    }

    private boolean isOrphanedDeletedAccount(User user) {
        return user.getOrgId() != null || user.isOnboardingComplete();
    }

    private User getOrCreateUser(OnboardingRequest req) {
        return findUserByIdentity(req.getClerkId(), req.getEmail()).orElseGet(() -> {
            if (!hasText(req.getClerkId())) {
                throw new IllegalArgumentException("Missing Clerk user ID");
            }
            if (!hasText(req.getEmail())) {
                throw new IllegalArgumentException("Missing user email");
            }

            User newUser = new User();
            newUser.setClerkId(req.getClerkId().trim());
            newUser.setEmail(normalizeEmail(req.getEmail()));
            newUser.setName(req.getName());
            return userRepository.save(newUser);
        });
    }

    private Optional<User> findUserByIdentity(String clerkId, String email) {
        String normalizedClerkId = trimToNull(clerkId);
        if (normalizedClerkId != null) {
            Optional<User> byClerkId = userRepository.findByClerkIdAndDeletedAtIsNull(normalizedClerkId);
            if (byClerkId.isPresent()) {
                return byClerkId;
            }
        }

        String normalizedEmail = normalizeEmail(email);
        if (normalizedEmail == null) {
            return Optional.empty();
        }

        return userRepository.findByEmailIgnoreCaseAndDeletedAtIsNull(normalizedEmail)
                .map(user -> relinkClerkIdIfNeeded(user, normalizedClerkId));
    }

    private User relinkClerkIdIfNeeded(User user, String clerkId) {
        if (clerkId == null || clerkId.equals(user.getClerkId())) {
            return user;
        }

        log.warn(
                "Relinking existing MoneyOps user to current Clerk identity. userId={}, email={}, oldClerkId={}, newClerkId={}",
                user.getId(),
                user.getEmail(),
                user.getClerkId(),
                clerkId
        );
        user.setClerkId(clerkId);
        return userRepository.save(user);
    }

    private OnboardingStatusResponse newUserResponse(String message) {
        return new OnboardingStatusResponse(false, null, null, message);
    }

    private String normalizeEmail(String email) {
        String trimmed = trimToNull(email);
        return trimmed == null ? null : trimmed.toLowerCase(Locale.ROOT);
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }

        String trimmed = value.trim();
        return trimmed.isBlank() ? null : trimmed;
    }

    private boolean hasText(String value) {
        return trimToNull(value) != null;
    }
}
