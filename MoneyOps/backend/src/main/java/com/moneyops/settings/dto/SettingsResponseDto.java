package com.moneyops.settings.dto;

import lombok.Data;

@Data
public class SettingsResponseDto {
    private ProfileSettingsDto profile;
    private BusinessSettingsDto business;
    private NotificationSettingsDto notifications;
    private SecuritySettingsDto security;
    private SettingsPermissionsDto permissions;
}
