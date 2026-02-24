package com.moneyops.onboarding.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class OnboardingStatusResponse {
    private boolean onboardingComplete;
    private String userId;
    private String orgId;
    private String message;
}
