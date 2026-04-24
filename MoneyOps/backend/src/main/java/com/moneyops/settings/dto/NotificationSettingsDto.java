package com.moneyops.settings.dto;

import lombok.Data;

@Data
public class NotificationSettingsDto {
    private boolean invoiceDue = true;
    private boolean paymentReceived = true;
    private boolean clientUpdates = false;
    private boolean weeklyReport = true;
    private boolean systemAlerts = true;
}
