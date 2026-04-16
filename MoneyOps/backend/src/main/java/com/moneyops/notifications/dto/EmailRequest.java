package com.moneyops.notifications.dto;

import lombok.Data;

import java.util.Map;

@Data
public class EmailRequest {
    private String type;
    private String recipientEmail;
    private String recipientName;
    private Map<String, Object> templateData;
}
