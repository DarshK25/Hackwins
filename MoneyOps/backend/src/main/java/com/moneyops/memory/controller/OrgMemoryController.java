package com.moneyops.memory.controller;

import com.moneyops.memory.entity.OrgMemory;
import com.moneyops.memory.service.OrgMemoryService;
import com.moneyops.shared.utils.OrgContext;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/memory")
@RequiredArgsConstructor
public class OrgMemoryController {

    private final OrgMemoryService orgMemoryService;

    @GetMapping("/{orgId}")
    public ResponseEntity<List<OrgMemory.MemoryItem>> getMemories(
            @PathVariable String orgId,
            @RequestParam(defaultValue = "5") int limit,
            @RequestParam(required = false) String query) {
        assertOrgAccess(orgId);
        return ResponseEntity.ok(orgMemoryService.getRelevantMemories(orgId, query, limit));
    }

    @PostMapping("/{orgId}")
    public ResponseEntity<OrgMemory.MemoryItem> saveMemory(
            @PathVariable String orgId,
            @RequestBody OrgMemoryService.SaveMemoryRequest request) {
        assertOrgAccess(orgId);
        String userId = OrgContext.getUserId();
        String source = request.getSource() != null && !request.getSource().isBlank()
                ? request.getSource()
                : (userId != null ? "user:" + userId : "conversation");
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(orgMemoryService.saveMemory(orgId, request, source));
    }

    private void assertOrgAccess(String pathOrgId) {
        String contextOrgId = OrgContext.getOrgId();
        if (contextOrgId == null || contextOrgId.isBlank()) {
            throw new com.moneyops.shared.exceptions.UnauthorizedException("Missing organization context");
        }
        if (!contextOrgId.equals(pathOrgId)) {
            throw new com.moneyops.shared.exceptions.ForbiddenException("Cross-organization memory access denied");
        }
    }
}
