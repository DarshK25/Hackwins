package com.moneyops.orchestrator.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OrchestratorSummaryDTO {
    private long totalTasks;
    private long completedTasks;
    private long failedTasks;
    private long pendingTasks;

    @Builder.Default
    private List<AgentBreakdownDTO> agentBreakdown = new ArrayList<>();

    @Builder.Default
    private List<RecentSessionDTO> recentSessions = new ArrayList<>();

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class AgentBreakdownDTO {
        private String agent;
        private long count;
        private int successRate;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class RecentSessionDTO {
        private String sessionId;
        private String summary;
        private String status;
        private LocalDateTime startedAt;
        private LocalDateTime endedAt;
        private Integer totalTurns;
        private int activityCount;
    }
}
