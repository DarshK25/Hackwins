package com.moneyops.settings.dto;

import lombok.Data;

@Data
public class ProfileSettingsDto {
    private String firstName;
    private String lastName;
    private String email;
    private String phone;
    private String professionalTitle;
}
