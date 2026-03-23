package com.moneyops.onboarding.service;

import com.moneyops.onboarding.dto.OnboardingRequest;
import com.moneyops.onboarding.dto.OnboardingStatusResponse;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.users.entity.User;
import com.moneyops.users.entity.Invite;
import com.moneyops.users.repository.UserRepository;
import com.moneyops.users.repository.InviteRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;
import java.util.Optional;
@Service
@RequiredArgsConstructor
@Slf4j
public class OnboardingService {

    private final UserRepository userRepository;
    private final BusinessOrganizationRepository orgRepository;
    private final InviteRepository inviteRepository;
    private final org.springframework.data.mongodb.core.MongoTemplate mongoTemplate;

    // ── Status check ──────────────────────────────────────────────────────────

    public OnboardingStatusResponse getStatus(String clerkId) {
        Optional<User> userOpt = userRepository.findByClerkIdAndDeletedAtIsNull(clerkId);

        if (userOpt.isEmpty()) {
            return new OnboardingStatusResponse(false, null, null, "New user — onboarding required");
        }

        User user = userOpt.get();
        String orgId = user.getOrgId();

        // Healing: If user has no orgId at all, check if they created one
        if (orgId == null) {
            log.info("User {} has no orgId, checking for created organizations", user.getEmail());
            var createdOrgs = orgRepository.findAllByCreatedByAndDeletedAtIsNull(user.getId());
            if (!createdOrgs.isEmpty()) {
                orgId = createdOrgs.get(0).getId();
                user.setOrgId(orgId);
                user.setOnboardingComplete(true);
                userRepository.save(user);
                log.info("Healed user {} with orgId {}", user.getEmail(), orgId);
            }
        }

        boolean hasOrg = orgId != null;
        boolean isComplete = user.isOnboardingComplete() || hasOrg;

        return new OnboardingStatusResponse(
                isComplete,
                user.getId(),
                hasOrg ? orgId : null,
                isComplete ? "Onboarding complete" : "Onboarding incomplete"
        );
    }

    // ── Create business ───────────────────────────────────────────────────────

    public OnboardingStatusResponse createBusiness(OnboardingRequest req) {
        log.info("Creating business for clerkId={}, legalName={}", req.getClerkId(), req.getLegalName());
        
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

        // Regulatory info
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

        // Context
        org.setPrimaryActivity(req.getPrimaryActivity());
        org.setTargetMarket(req.getTargetMarket());
        org.setKeyProducts(req.getKeyProducts());
        org.setCurrentChallenges(req.getCurrentChallenges());
        org.setAccountingMethod(req.getAccountingMethod());
        org.setFyStartMonth(req.getFyStartMonth() != null ? req.getFyStartMonth() : 4);
        org.setPreferredLanguage(req.getPreferredLanguage() != null ? req.getPreferredLanguage() : "en");

        User user = getOrCreateUser(req);
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

    // ── Join business ─────────────────────────────────────────────────────────

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

        // Mark invite as accepted
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

    private User getOrCreateUser(OnboardingRequest req) {
        return userRepository.findByClerkIdAndDeletedAtIsNull(req.getClerkId()).orElseGet(() -> {
            User newUser = new User();
            newUser.setClerkId(req.getClerkId());
            newUser.setEmail(req.getEmail());
            newUser.setName(req.getName());
            newUser.setPasswordHash("");
            // Audit populated by @EnableMongoAuditing
            return userRepository.save(newUser);
        });
    }
}
