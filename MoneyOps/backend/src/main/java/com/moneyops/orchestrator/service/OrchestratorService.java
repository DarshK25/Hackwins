package com.moneyops.orchestrator.service;

import com.moneyops.orchestrator.dto.ActivityDTO;
import com.moneyops.orchestrator.dto.OrchestratorSummaryDTO;
import com.moneyops.orchestrator.entity.OrchestratorActivity;
import com.moneyops.orchestrator.entity.VoiceConversation;
import com.moneyops.orchestrator.repository.OrchestratorActivityRepository;
import com.moneyops.orchestrator.repository.VoiceConversationRepository;
import com.moneyops.shared.dto.PageResponse;
import com.moneyops.shared.exceptions.NotFoundException;
import com.moneyops.shared.exceptions.UnauthorizedException;
import com.moneyops.shared.exceptions.ValidationException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.FindAndModifyOptions;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;
import org.springframework.data.mongodb.core.query.Update;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class OrchestratorService {

    private static final Set<String> COMPLETED_STATUSES = Set.of("COMPLETED", "SUCCESS");
    private static final Set<String> FAILED_STATUSES = Set.of("FAILED", "ERROR");
    private static final Set<String> PENDING_STATUSES = Set.of("PENDING", "IN_PROGRESS", "PROCESSING", "ACTIVE");

    private final OrchestratorActivityRepository activityRepo;
    private final VoiceConversationRepository conversationRepo;
    private final MongoTemplate mongoTemplate;

    public PageResponse<ActivityDTO> getActivities(String orgId, int page, int size) {
        PageRequest pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<ActivityDTO> resultPage = activityRepo.findByOrgIdOrderByTimestampDesc(requireOrgId(orgId), pageable)
                .map(this::toActivityDto);
        return PageResponse.from(resultPage);
    }

    public List<ActivityDTO> getActivitiesByAgent(String orgId, String agentName) {
        if (agentName == null || agentName.isBlank()) {
            throw new ValidationException(List.of("Agent name is required"));
        }

        return activityRepo.findByOrgIdAndAgentOrderByTimestampDesc(requireOrgId(orgId), agentName.trim()).stream()
                .map(this::toActivityDto)
                .toList();
    }

    public Map<String, Object> getSessionTimeline(String orgId, String sessionId) {
        if (sessionId == null || sessionId.isBlank()) {
            throw new ValidationException(List.of("Session ID is required"));
        }

        VoiceConversation conversation = findLatestConversation(sessionId, requireOrgId(orgId))
                .orElseThrow(() -> new NotFoundException("Voice conversation", sessionId));

        List<ActivityDTO> activities = activityRepo.findByOrgIdAndSessionIdOrderByTimestampAsc(orgId, sessionId).stream()
                .map(this::toActivityDto)
                .toList();

        Map<String, Object> timeline = new LinkedHashMap<>();
        timeline.put("sessionId", conversation.getSessionId());
        timeline.put("summary", conversation.getSummary());
        timeline.put("status", normalizeStatus(conversation.getStatus()));
        timeline.put("startedAt", conversation.getStartedAt());
        timeline.put("endedAt", conversation.getEndedAt());
        timeline.put("duration", conversation.getDuration());
        timeline.put("totalTurns", conversation.getTotalTurns());
        timeline.put("tasksGenerated", conversation.getTasksGenerated());
        timeline.put("messages", conversation.getMessages());
        timeline.put("activities", activities);
        return timeline;
    }

    public OrchestratorSummaryDTO getSummary(String orgId) {
        String resolvedOrgId = requireOrgId(orgId);
        List<OrchestratorActivity> activities = activityRepo.findByOrgIdOrderByTimestampDesc(resolvedOrgId);
        List<VoiceConversation> recentConversations = conversationRepo.findByOrgIdOrderByStartedAtDesc(resolvedOrgId);

        long completedTasks = activities.stream().filter(activity -> isCompleted(activity.getStatus())).count();
        long failedTasks = activities.stream().filter(activity -> isFailed(activity.getStatus())).count();
        long pendingTasks = activities.stream().filter(activity -> isPending(activity.getStatus())).count();

        List<OrchestratorSummaryDTO.AgentBreakdownDTO> breakdown = activities.stream()
                .filter(activity -> activity.getAgent() != null && !activity.getAgent().isBlank())
                .collect(Collectors.groupingBy(
                        OrchestratorActivity::getAgent,
                        LinkedHashMap::new,
                        Collectors.toList()
                ))
                .entrySet()
                .stream()
                .map(entry -> {
                    long successful = entry.getValue().stream()
                            .filter(activity -> isCompleted(activity.getStatus()))
                            .count();
                    int successRate = entry.getValue().isEmpty()
                            ? 0
                            : (int) Math.round((successful * 100.0) / entry.getValue().size());
                    return OrchestratorSummaryDTO.AgentBreakdownDTO.builder()
                            .agent(entry.getKey())
                            .count(entry.getValue().size())
                            .successRate(successRate)
                            .build();
                })
                .sorted((left, right) -> Long.compare(right.getCount(), left.getCount()))
                .toList();

        List<OrchestratorSummaryDTO.RecentSessionDTO> recentSessions = recentConversations.stream()
                .limit(5)
                .map(conversation -> OrchestratorSummaryDTO.RecentSessionDTO.builder()
                        .sessionId(conversation.getSessionId())
                        .summary(conversation.getSummary())
                        .status(normalizeStatus(conversation.getStatus()))
                        .startedAt(conversation.getStartedAt())
                        .endedAt(conversation.getEndedAt())
                        .totalTurns(conversation.getTotalTurns())
                        .activityCount(activityRepo.findByOrgIdAndSessionIdOrderByTimestampAsc(
                                resolvedOrgId,
                                conversation.getSessionId()
                        ).size())
                        .build())
                .toList();

        return OrchestratorSummaryDTO.builder()
                .totalTasks(activities.size())
                .completedTasks(completedTasks)
                .failedTasks(failedTasks)
                .pendingTasks(pendingTasks)
                .agentBreakdown(breakdown)
                .recentSessions(recentSessions)
                .build();
    }

    public List<OrchestratorActivity> getRecentActivities(String orgId, int limitDays) {
        LocalDateTime since = LocalDateTime.now().minusDays(limitDays);
        return activityRepo.findByOrgIdAndTimestampAfterOrderByTimestampDesc(requireOrgId(orgId), since);
    }

    public ActivityDTO logActivity(ActivityDTO request, String fallbackOrgId, String fallbackUserId) {
        if (request == null) {
            throw new ValidationException(List.of("Activity payload is required"));
        }

        String resolvedOrgId = requireOrgId(firstNonBlank(request.getOrgId(), fallbackOrgId));
        if (request.getType() == null || request.getType().isBlank()) {
            throw new ValidationException(List.of("Activity type is required"));
        }
        if (request.getDescription() == null || request.getDescription().isBlank()) {
            throw new ValidationException(List.of("Activity description is required"));
        }

        OrchestratorActivity activity = new OrchestratorActivity();
        activity.setOrgId(resolvedOrgId);
        activity.setUserId(firstNonBlank(request.getUserId(), fallbackUserId));
        activity.setType(request.getType().trim().toUpperCase());
        activity.setDescription(request.getDescription().trim());
        activity.setAgent(firstNonBlank(request.getAgentName(), "Orchestrator"));
        activity.setStatus(normalizeStatus(request.getStatus()));
        activity.setIntent(normalizeNullable(request.getIntent()));
        activity.setSessionId(trimToNull(request.getSessionId()));
        activity.setTimestamp(request.getTimestamp() != null ? request.getTimestamp() : LocalDateTime.now());
        return toActivityDto(activityRepo.save(activity));
    }

    public List<VoiceConversation> getConversations(String orgId, int limitDays) {
        LocalDateTime since = LocalDateTime.now().minusDays(limitDays);
        return conversationRepo.findByOrgIdAndStartedAtAfterOrderByStartedAtDesc(requireOrgId(orgId), since);
    }

    public long countConversationsToday(String orgId) {
        LocalDateTime startOfDay = LocalDate.now().atStartOfDay();
        return conversationRepo.countByOrgIdAndStartedAtAfter(requireOrgId(orgId), startOfDay);
    }

    public VoiceConversation startConversation(String orgId, String userId, String sessionId) {
        String resolvedOrgId = requireOrgId(orgId);
        Query query = new Query(Criteria.where("sessionId").is(sessionId).and("orgId").is(resolvedOrgId));
        query.with(Sort.by(Sort.Direction.DESC, "startedAt"));

        Update update = new Update()
                .setOnInsert("orgId", resolvedOrgId)
                .setOnInsert("userId", userId)
                .setOnInsert("sessionId", sessionId)
                .setOnInsert("status", "active")
                .setOnInsert("startedAt", LocalDateTime.now())
                .setOnInsert("messages", List.of())
                .setOnInsert("tasksGenerated", List.of())
                .setOnInsert("totalTurns", 0);

        VoiceConversation conversation = mongoTemplate.findAndModify(
                query,
                update,
                FindAndModifyOptions.options().returnNew(true).upsert(true),
                VoiceConversation.class
        );

        if (conversation != null) {
            return conversation;
        }

        return findLatestConversation(sessionId, resolvedOrgId)
                .orElseThrow(() -> new NotFoundException("Voice conversation", sessionId));
    }

    public VoiceConversation addMessage(String sessionId, String orgId, String role, String content, String intent) {
        Optional<VoiceConversation> existing = findLatestConversation(sessionId, requireOrgId(orgId));
        if (existing.isEmpty()) {
            log.warn("Voice conversation not found for session={}", sessionId);
            throw new NotFoundException("Voice conversation", sessionId);
        }

        VoiceConversation conversation = existing.get();
        VoiceConversation.Message message = new VoiceConversation.Message();
        message.setRole(role);
        message.setContent(content);
        message.setIntent(intent);
        message.setTimestamp(LocalDateTime.now());
        conversation.getMessages().add(message);
        conversation.setTotalTurns(conversation.getMessages().size());
        return conversationRepo.save(conversation);
    }

    public VoiceConversation endConversation(String sessionId, String orgId, String summary, List<String> tasksGenerated) {
        Optional<VoiceConversation> existing = findLatestConversation(sessionId, requireOrgId(orgId));
        if (existing.isEmpty()) {
            throw new NotFoundException("Voice conversation", sessionId);
        }

        VoiceConversation conversation = existing.get();
        conversation.setStatus("completed");
        conversation.setEndedAt(LocalDateTime.now());
        conversation.setSummary(summary);
        if (tasksGenerated != null) {
            conversation.setTasksGenerated(tasksGenerated);
        }

        if (conversation.getStartedAt() != null) {
            long durationSeconds = java.time.Duration.between(conversation.getStartedAt(), conversation.getEndedAt()).getSeconds();
            conversation.setDuration((int) durationSeconds);
        }
        return conversationRepo.save(conversation);
    }

    public Map<String, Object> getAgentStats(String orgId) {
        List<OrchestratorActivity> activities = activityRepo.findByOrgIdOrderByTimestampDesc(requireOrgId(orgId));
        long completedCount = activities.stream().filter(activity -> isCompleted(activity.getStatus())).count();

        Map<String, Long> perAgent = new LinkedHashMap<>();
        for (OrchestratorActivity activity : activities) {
            if (activity.getAgent() != null && isCompleted(activity.getStatus())) {
                perAgent.merge(activity.getAgent(), 1L, Long::sum);
            }
        }

        int efficiencyScore = activities.isEmpty()
                ? 100
                : (int) Math.round((completedCount * 100.0) / activities.size());

        return Map.of(
                "totalTasksCompleted", completedCount,
                "efficiencyScore", efficiencyScore,
                "perAgent", perAgent
        );
    }

    private ActivityDTO toActivityDto(OrchestratorActivity activity) {
        return ActivityDTO.builder()
                .id(activity.getId())
                .orgId(activity.getOrgId())
                .userId(activity.getUserId())
                .type(activity.getType())
                .description(activity.getDescription())
                .agentName(activity.getAgent())
                .status(normalizeStatus(activity.getStatus()))
                .intent(activity.getIntent())
                .sessionId(activity.getSessionId())
                .timestamp(activity.getTimestamp())
                .build();
    }

    private Optional<VoiceConversation> findLatestConversation(String sessionId, String orgId) {
        List<VoiceConversation> conversations =
                conversationRepo.findBySessionIdAndOrgIdOrderByStartedAtDesc(sessionId, orgId);
        if (conversations.size() > 1) {
            log.warn(
                    "Found {} voice conversations for session={} org={}; using latest",
                    conversations.size(),
                    sessionId,
                    orgId
            );
        }
        return conversations.stream().findFirst();
    }

    private String requireOrgId(String orgId) {
        if (orgId == null || orgId.isBlank()) {
            throw new UnauthorizedException("Missing organization context");
        }
        return orgId;
    }

    private boolean isCompleted(String status) {
        return COMPLETED_STATUSES.contains(normalizeStatus(status));
    }

    private boolean isFailed(String status) {
        return FAILED_STATUSES.contains(normalizeStatus(status));
    }

    private boolean isPending(String status) {
        return PENDING_STATUSES.contains(normalizeStatus(status));
    }

    private String normalizeStatus(String status) {
        return firstNonBlank(status, "PENDING").trim().toUpperCase();
    }

    private String normalizeNullable(String value) {
        String trimmed = trimToNull(value);
        return trimmed == null ? null : trimmed.toUpperCase();
    }

    private String firstNonBlank(String primary, String fallback) {
        String primaryValue = trimToNull(primary);
        return primaryValue != null ? primaryValue : fallback;
    }

    private String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isBlank() ? null : trimmed;
    }
}
