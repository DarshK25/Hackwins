package com.moneyops.onboarding.service;

import com.moneyops.onboarding.dto.OnboardingRequest;
import com.moneyops.onboarding.dto.OnboardingStatusResponse;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
@Slf4j
public class OnboardingService {

    private final UserRepository userRepository;
    private final BusinessOrganizationRepository orgRepository;

    // ── Status check ──────────────────────────────────────────────────────────

    /**
     * Check if a Clerk user has already completed onboarding.
     * Called on every sign-in to decide which screen to show.
     */
    public OnboardingStatusResponse getStatus(String clerkId) {
        Optional<User> userOpt = userRepository.findByClerkId(clerkId);

        if (userOpt.isEmpty()) {
            // Brand new user — never seen before
            return new OnboardingStatusResponse(false, null, null, "New user — onboarding required");
        }

        User user = userOpt.get();

        // If the user has an orgId, they have completed onboarding — even if the flag
        // was never explicitly set to true (e.g. legacy records or interrupted flows).
        boolean hasOrg = user.getOrgId() != null;
        boolean isComplete = user.isOnboardingComplete() || hasOrg;

        // Auto-heal: persist the corrected flag so future checks are instant
        if (hasOrg && !user.isOnboardingComplete()) {
            log.info("Auto-healing onboardingComplete flag for clerkId={}", clerkId);
            user.setOnboardingComplete(true);
            userRepository.save(user);
        }

        return new OnboardingStatusResponse(
                isComplete,
                user.getId().toString(),
                hasOrg ? user.getOrgId().toString() : null,
                isComplete ? "Onboarding complete" : "Onboarding incomplete"
        );
    }

    // ── Create business ───────────────────────────────────────────────────────

    public OnboardingStatusResponse createBusiness(OnboardingRequest req) {

        BusinessOrganization org = new BusinessOrganization();

        // ── Step 1: Business Info ─────────────────────────────────────────────
        org.setLegalName(req.getLegalName());
        org.setTradingName(req.getTradingName());
        org.setBusinessType(req.getBusinessType());       // stored as-is: "sole_proprietorship" etc.
        org.setIndustry(req.getIndustry());               // stored as-is: "it_software" etc.
        if (req.getRegistrationDate() != null && !req.getRegistrationDate().isEmpty()) {
            org.setRegistrationDate(java.time.LocalDate.parse(req.getRegistrationDate()));
        }
        org.setAnnualTurnover(req.getAnnualTurnover());   // stored as-is: "below_10l" etc.
        org.setPrimaryEmail(req.getPrimaryEmail());
        org.setPrimaryPhone(req.getPrimaryPhone());
        org.setWebsite(req.getWebsite());
        org.setEmployeeCount(req.getNumberOfEmployees());
        org.setRegisteredAddress(req.getRegisteredAddress());

        // ── Step 2: Regulatory Info ───────────────────────────────────────────
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

        // ── Step 3: Business Context ──────────────────────────────────────────
        org.setPrimaryActivity(req.getPrimaryActivity());
        org.setTargetMarket(req.getTargetMarket());       // stored as-is: "B2B" | "B2C" | "B2G"
        org.setKeyProducts(req.getKeyProducts());
        org.setCurrentChallenges(req.getCurrentChallenges());
        org.setAccountingMethod(req.getAccountingMethod()); // "accrual" | "cash"
        org.setFyStartMonth(req.getFyStartMonth() != null ? req.getFyStartMonth() : 4);
        org.setPreferredLanguage(req.getPreferredLanguage() != null ? req.getPreferredLanguage() : "en");

        // ── Audit ─────────────────────────────────────────────────────────────
        User user = getOrCreateUser(req);
        org.setCreatedBy(user.getId());

        // Save org to MongoDB
        BusinessOrganization savedOrg = orgRepository.save(org);
        log.info("Saved org id={} name={} for user={}", savedOrg.getId(), savedOrg.getLegalName(), user.getId());

        // Link user → org, mark onboarding done
        user.setOrgId(savedOrg.getId());
        user.setOnboardingComplete(true);
        user.setRole(User.Role.OWNER);
        userRepository.save(user);

        return new OnboardingStatusResponse(
                true,
                user.getId().toString(),
                savedOrg.getId().toString(),
                "Business created successfully"
        );
    }


    // ── Join business ─────────────────────────────────────────────────────────

    public OnboardingStatusResponse joinBusiness(OnboardingRequest req) {
        // Find the organisation by invite code (invite code = org ID for now)
        UUID orgId;
        try {
            orgId = UUID.fromString(req.getInviteCode());
        } catch (IllegalArgumentException e) {
            throw new RuntimeException("Invalid invite code");
        }

        BusinessOrganization org = orgRepository.findById(orgId)
                .orElseThrow(() -> new RuntimeException("Organisation not found for invite code: " + req.getInviteCode()));

        User user = getOrCreateUser(req);
        user.setOrgId(org.getId());
        user.setOnboardingComplete(true);
        user.setRole(User.Role.STAFF);
        userRepository.save(user);

        log.info("User {} joined org {}", user.getId(), org.getId());

        return new OnboardingStatusResponse(
                true,
                user.getId().toString(),
                org.getId().toString(),
                "Joined organisation successfully"
        );
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private User getOrCreateUser(OnboardingRequest req) {
        return userRepository.findByClerkId(req.getClerkId()).orElseGet(() -> {
            User newUser = new User();
            newUser.setClerkId(req.getClerkId());
            newUser.setEmail(req.getEmail());
            newUser.setName(req.getName());
            newUser.setPasswordHash(""); // not used — auth is via Clerk
            newUser.setCreatedBy(newUser.getId());
            newUser.setUpdatedBy(newUser.getId());
            return userRepository.save(newUser);
        });
    }
}
