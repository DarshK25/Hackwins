package com.moneyops.onboarding.controller;

import com.moneyops.onboarding.dto.OnboardingRequest;
import com.moneyops.onboarding.dto.OnboardingStatusResponse;
import com.moneyops.onboarding.service.OnboardingService;
import com.moneyops.shared.dto.ApiResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * Onboarding endpoints — called by the frontend after Clerk sign-in.
 */
@RestController
@RequestMapping("/api/onboarding")
@RequiredArgsConstructor
public class OnboardingController {

    private final OnboardingService onboardingService;

    @GetMapping("/status")
    public ResponseEntity<ApiResponse<OnboardingStatusResponse>> getStatus(
            @RequestParam String clerkId,
            @RequestParam(required = false) String email,
            @RequestHeader(value = "X-User-Email", required = false) String emailHeader) {
        OnboardingStatusResponse status = onboardingService.getStatus(
                clerkId,
                email != null && !email.isBlank() ? email : emailHeader
        );
        return ResponseEntity.ok(ApiResponse.success(status));
    }

    @PostMapping("/create-business")
    public ResponseEntity<ApiResponse<OnboardingStatusResponse>> createBusiness(
            @RequestBody OnboardingRequest request) {
        OnboardingStatusResponse result = onboardingService.createBusiness(request);
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    @PostMapping("/join-business")
    public ResponseEntity<ApiResponse<OnboardingStatusResponse>> joinBusiness(
            @RequestBody OnboardingRequest request) {
        OnboardingStatusResponse result = onboardingService.joinBusiness(request);
        return ResponseEntity.ok(ApiResponse.success(result));
    }

    @PostMapping("/verify-invite")
    public ResponseEntity<ApiResponse<Map<String, Object>>> verifyInvite(
            @RequestBody Map<String, String> request) {
        Map<String, Object> result = onboardingService.verifyInvite(request.get("code"));
        return ResponseEntity.ok(ApiResponse.success(result));
    }
}
