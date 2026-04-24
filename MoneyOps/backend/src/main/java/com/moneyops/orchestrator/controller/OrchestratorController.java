package com.moneyops.orchestrator.controller;

import com.moneyops.orchestrator.dto.ActivityDTO;
import com.moneyops.orchestrator.dto.OrchestratorSummaryDTO;
import com.moneyops.orchestrator.entity.VoiceConversation;
import com.moneyops.orchestrator.service.OrchestratorService;
import com.moneyops.shared.dto.ApiResponse;
import com.moneyops.shared.dto.PageResponse;
import com.moneyops.shared.utils.OrgContext;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/orchestrator")
@RequiredArgsConstructor
public class OrchestratorController {

    private final OrchestratorService orchestratorService;

    @GetMapping("/activities")
    public ResponseEntity<ApiResponse<PageResponse<ActivityDTO>>> getActivities(
            @RequestParam(required = false) String orgId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size
    ) {
        return ResponseEntity.ok(ApiResponse.success(
                orchestratorService.getActivities(resolveOrgId(orgId), page, size)
        ));
    }

    @GetMapping("/activities/agent/{agentName}")
    public ResponseEntity<ApiResponse<List<ActivityDTO>>> getActivitiesByAgent(
            @PathVariable String agentName,
            @RequestParam(required = false) String orgId
    ) {
        return ResponseEntity.ok(ApiResponse.success(
                orchestratorService.getActivitiesByAgent(resolveOrgId(orgId), agentName)
        ));
    }

    @GetMapping("/activities/session/{sessionId}")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getSessionTimeline(
            @PathVariable String sessionId,
            @RequestParam(required = false) String orgId
    ) {
        return ResponseEntity.ok(ApiResponse.success(
                orchestratorService.getSessionTimeline(resolveOrgId(orgId), sessionId)
        ));
    }

    @PostMapping("/activities")
    public ResponseEntity<ApiResponse<ActivityDTO>> logActivity(@RequestBody ActivityDTO request) {
        return ResponseEntity.ok(ApiResponse.success(
                "Activity logged successfully",
                orchestratorService.logActivity(request, OrgContext.getOrgId(), OrgContext.getUserId())
        ));
    }

    @GetMapping("/summary")
    public ResponseEntity<ApiResponse<OrchestratorSummaryDTO>> getSummary(
            @RequestParam(required = false) String orgId
    ) {
        return ResponseEntity.ok(ApiResponse.success(
                orchestratorService.getSummary(resolveOrgId(orgId))
        ));
    }

    @GetMapping("/conversations")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getConversations(
            @RequestParam(required = false) String orgId,
            @RequestParam(defaultValue = "30") int days
    ) {
        String resolvedOrgId = resolveOrgId(orgId);
        List<VoiceConversation> conversations = orchestratorService.getConversations(resolvedOrgId, days);
        long todayCount = orchestratorService.countConversationsToday(resolvedOrgId);
        return ResponseEntity.ok(ApiResponse.success(Map.of(
                "conversations", conversations,
                "total", conversations.size(),
                "todayCount", todayCount
        )));
    }

    @PostMapping("/conversations/start")
    public ResponseEntity<ApiResponse<VoiceConversation>> startConversation(@RequestBody ConversationStartRequest request) {
        return ResponseEntity.ok(ApiResponse.success(
                orchestratorService.startConversation(
                        resolveOrgId(request.getOrgId()),
                        resolveUserId(request.getUserId()),
                        request.getSessionId()
                )
        ));
    }

    @PostMapping("/conversations/message")
    public ResponseEntity<ApiResponse<VoiceConversation>> addMessage(@RequestBody MessageRequest request) {
        return ResponseEntity.ok(ApiResponse.success(
                orchestratorService.addMessage(
                        request.getSessionId(),
                        resolveOrgId(request.getOrgId()),
                        request.getRole(),
                        request.getContent(),
                        request.getIntent()
                )
        ));
    }

    @PostMapping("/conversations/end")
    public ResponseEntity<ApiResponse<VoiceConversation>> endConversation(@RequestBody ConversationEndRequest request) {
        return ResponseEntity.ok(ApiResponse.success(
                orchestratorService.endConversation(
                        request.getSessionId(),
                        resolveOrgId(request.getOrgId()),
                        request.getSummary(),
                        request.getTasksGenerated()
                )
        ));
    }

    @GetMapping("/stats")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getStats(
            @RequestParam(required = false) String orgId
    ) {
        return ResponseEntity.ok(ApiResponse.success(
                orchestratorService.getAgentStats(resolveOrgId(orgId))
        ));
    }

    private String resolveOrgId(String fallbackOrgId) {
        return OrgContext.getOrgId() != null ? OrgContext.getOrgId() : fallbackOrgId;
    }

    private String resolveUserId(String fallbackUserId) {
        return OrgContext.getUserId() != null ? OrgContext.getUserId() : fallbackUserId;
    }

    @Data
    public static class ConversationStartRequest {
        private String orgId;
        private String userId;
        private String sessionId;
    }

    @Data
    public static class MessageRequest {
        private String orgId;
        private String sessionId;
        private String role;
        private String content;
        private String intent;
    }

    @Data
    public static class ConversationEndRequest {
        private String orgId;
        private String sessionId;
        private String summary;
        private List<String> tasksGenerated;
    }
}
