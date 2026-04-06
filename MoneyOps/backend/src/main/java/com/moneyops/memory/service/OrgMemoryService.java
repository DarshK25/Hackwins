package com.moneyops.memory.service;

import com.moneyops.memory.entity.OrgMemory;
import com.moneyops.memory.repository.OrgMemoryRepository;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class OrgMemoryService {

    private final OrgMemoryRepository orgMemoryRepository;

    @Data
    public static class SaveMemoryRequest {
        private String content;
        private String type;
        private List<String> tags = new ArrayList<>();
        private String source;
    }

    public OrgMemory.MemoryItem saveMemory(String orgId, SaveMemoryRequest request, String source) {
        if (request.getContent() == null || request.getContent().isBlank()) {
            throw new IllegalArgumentException("Memory content is required");
        }
        if (request.getType() == null || request.getType().isBlank()) {
            throw new IllegalArgumentException("Memory type is required");
        }

        OrgMemory orgMemory = orgMemoryRepository.findByOrgId(orgId)
                .orElseGet(() -> {
                    OrgMemory created = new OrgMemory();
                    created.setOrgId(orgId);
                    return created;
                });

        String normalizedContent = request.getContent().trim();
        LocalDateTime now = LocalDateTime.now();

        OrgMemory.MemoryItem existing = orgMemory.getMemories().stream()
                .filter(memory -> memory.getType() != null && memory.getType().equalsIgnoreCase(request.getType()))
                .filter(memory -> memory.getContent() != null && memory.getContent().trim().equalsIgnoreCase(normalizedContent))
                .findFirst()
                .orElse(null);

        if (existing != null) {
            existing.setLastReferencedAt(now);
            existing.setSource(source != null ? source : existing.getSource());
            existing.setTags(mergeTags(existing.getTags(), request.getTags()));
            orgMemoryRepository.save(orgMemory);
            return existing;
        }

        OrgMemory.MemoryItem memoryItem = new OrgMemory.MemoryItem();
        memoryItem.setId("mem_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12));
        memoryItem.setType(request.getType());
        memoryItem.setContent(normalizedContent);
        memoryItem.setSource(source != null ? source : "conversation");
        memoryItem.setCreatedAt(now);
        memoryItem.setLastReferencedAt(now);
        memoryItem.setTags(mergeTags(List.of(), request.getTags()));

        orgMemory.getMemories().add(memoryItem);
        orgMemoryRepository.save(orgMemory);
        return memoryItem;
    }

    public List<OrgMemory.MemoryItem> getRelevantMemories(String orgId, String query, int limit) {
        OrgMemory orgMemory = orgMemoryRepository.findByOrgId(orgId)
                .orElseGet(() -> {
                    OrgMemory empty = new OrgMemory();
                    empty.setOrgId(orgId);
                    return empty;
                });

        List<OrgMemory.MemoryItem> memories = new ArrayList<>(orgMemory.getMemories());
        Comparator<OrgMemory.MemoryItem> comparator;
        if (query == null || query.isBlank()) {
            comparator = Comparator
                    .comparing(OrgMemory.MemoryItem::getLastReferencedAt, Comparator.nullsLast(Comparator.reverseOrder()))
                    .thenComparing(OrgMemory.MemoryItem::getCreatedAt, Comparator.nullsLast(Comparator.reverseOrder()));
        } else {
            comparator = Comparator
                    .comparingInt((OrgMemory.MemoryItem item) -> score(item, query))
                    .reversed()
                    .thenComparing(OrgMemory.MemoryItem::getLastReferencedAt, Comparator.nullsLast(Comparator.reverseOrder()));
            memories = memories.stream()
                    .filter(item -> score(item, query) > 0)
                    .collect(Collectors.toList());
        }

        List<OrgMemory.MemoryItem> selected = memories.stream()
                .sorted(comparator)
                .limit(Math.max(1, limit))
                .collect(Collectors.toList());

        if (!selected.isEmpty()) {
            LocalDateTime now = LocalDateTime.now();
            Set<String> selectedIds = selected.stream().map(OrgMemory.MemoryItem::getId).collect(Collectors.toSet());
            orgMemory.getMemories().stream()
                    .filter(item -> selectedIds.contains(item.getId()))
                    .forEach(item -> item.setLastReferencedAt(now));
            orgMemoryRepository.save(orgMemory);
        }

        return selected;
    }

    private int score(OrgMemory.MemoryItem item, String query) {
        String normalizedQuery = query.toLowerCase(Locale.ROOT);
        String content = item.getContent() == null ? "" : item.getContent().toLowerCase(Locale.ROOT);
        String type = item.getType() == null ? "" : item.getType().toLowerCase(Locale.ROOT);
        List<String> tags = item.getTags() == null ? List.of() : item.getTags();

        int score = 0;
        for (String token : normalizedQuery.split("\\s+")) {
            if (token.length() < 3) {
                continue;
            }
            if (content.contains(token)) {
                score += 5;
            }
            if (type.contains(token)) {
                score += 3;
            }
            if (tags.stream().anyMatch(tag -> tag != null && tag.toLowerCase(Locale.ROOT).contains(token))) {
                score += 4;
            }
        }
        return score;
    }

    private List<String> mergeTags(List<String> existingTags, List<String> newTags) {
        return java.util.stream.Stream.concat(
                        existingTags == null ? java.util.stream.Stream.empty() : existingTags.stream(),
                        newTags == null ? java.util.stream.Stream.empty() : newTags.stream()
                )
                .filter(tag -> tag != null && !tag.isBlank())
                .map(tag -> tag.trim().toLowerCase(Locale.ROOT))
                .distinct()
                .collect(Collectors.toList());
    }
}
