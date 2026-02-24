package com.moneyops.onboarding.controller;

import com.moneyops.onboarding.dto.OnboardingRequest;
import com.moneyops.onboarding.dto.OnboardingStatusResponse;
import com.moneyops.onboarding.service.OnboardingService;
import com.moneyops.shared.dto.ApiResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * Onboarding endpoints — called by the frontend after Clerk sign-in.
 *
 * All endpoints receive the Clerk user's ID and email in a header.
 * We do NOT use our own JWT here; Clerk sessions are trusted on the frontend.
 * The backend stores the clerkId so future requests can be resolved.
 */
@RestController
@RequestMapping("/api/onboarding")
@RequiredArgsConstructor
public class OnboardingController {

    private final OnboardingService onboardingService;

    /**
     * GET /api/onboarding/status?clerkId={clerkId}
     * Returns whether this Clerk user has completed onboarding.
     * Called immediately after sign-in to decide: show dashboard or onboarding.
     */
    @GetMapping("/status")
    public ResponseEntity<ApiResponse<OnboardingStatusResponse>> getStatus(
            @RequestParam String clerkId) {
        OnboardingStatusResponse status = onboardingService.getStatus(clerkId);
        return ResponseEntity.ok(ApiResponse.success(status));
    }

    /**
     * POST /api/onboarding/create-business
     * Creates a new organisation + marks the user as onboarded.
     */
    @PostMapping("/create-business")
    public ResponseEntity<ApiResponse<OnboardingStatusResponse>> createBusiness(
            @RequestBody OnboardingRequest request) {
        OnboardingStatusResponse result = onboardingService.createBusiness(request);
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    /**
     * POST /api/onboarding/join-business
     * Joins an existing organisation via invite code + marks the user as onboarded.
     */
    @PostMapping("/join-business")
    public ResponseEntity<ApiResponse<OnboardingStatusResponse>> joinBusiness(
            @RequestBody OnboardingRequest request) {
        OnboardingStatusResponse result = onboardingService.joinBusiness(request);
        return ResponseEntity.ok(ApiResponse.success(result));
    }
}
