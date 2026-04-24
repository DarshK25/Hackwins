package com.moneyops.settings.dto;

import lombok.Data;

@Data
public class SecuritySettingsDto {
    private boolean clerkManagedAuth = true;
    private boolean teamSecurityCodeConfigured;
    private boolean deleteRequiresTeamActionCode = true;
}
