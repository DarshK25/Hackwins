package com.moneyops.settings.dto;

import lombok.Data;

@Data
public class SettingsPermissionsDto {
    private boolean canEditBusiness;
    private boolean canDeleteAccount;
}
