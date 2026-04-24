package com.moneyops.orchestrator.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ActivityDTO {
    private String id;
    private String orgId;
    private String userId;
    private String type;
    private String description;
    private String agentName;
    private String status;
    private String intent;
    private String sessionId;
    private LocalDateTime timestamp;
}
