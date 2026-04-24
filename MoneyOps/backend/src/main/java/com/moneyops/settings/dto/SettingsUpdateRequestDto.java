package com.moneyops.settings.dto;

import lombok.Data;

@Data
public class SettingsUpdateRequestDto {
    private String section;
    private ProfileSettingsDto profile;
    private BusinessSettingsDto business;
    private NotificationSettingsDto notifications;
}
