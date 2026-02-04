// src/main/java/com/moneyops/organizations/controller/RegulatoryController.java
package com.moneyops.organizations.controller;

import com.moneyops.organizations.dto.RegulatoryProfileDto;
import com.moneyops.organizations.service.OrganizationService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/org/{orgId}/regulatory")
@RequiredArgsConstructor
public class RegulatoryController {

    private final OrganizationService organizationService;

    @PostMapping
    public ResponseEntity<RegulatoryProfileDto> createRegulatoryProfile(@PathVariable UUID orgId,
                                                                         @RequestBody RegulatoryProfileDto dto,
                                                                         @RequestHeader("X-User-Id") UUID userId) {
        RegulatoryProfileDto created = organizationService.createRegulatoryProfile(orgId, dto, userId);
        return ResponseEntity.ok(created);
    }

    @PutMapping
    public ResponseEntity<RegulatoryProfileDto> updateRegulatoryProfile(@PathVariable UUID orgId,
                                                                         @RequestBody RegulatoryProfileDto dto,
                                                                         @RequestHeader("X-User-Id") UUID userId) {
        RegulatoryProfileDto updated = organizationService.updateRegulatoryProfile(orgId, dto, userId);
        return ResponseEntity.ok(updated);
    }

    @PatchMapping
    public ResponseEntity<RegulatoryProfileDto> partialUpdateRegulatoryProfile(@PathVariable UUID orgId,
                                                                                @RequestBody RegulatoryProfileDto dto,
                                                                                @RequestHeader("X-User-Id") UUID userId) {
        // For partial update
        RegulatoryProfileDto updated = organizationService.updateRegulatoryProfile(orgId, dto, userId);
        return ResponseEntity.ok(updated);
    }

    @GetMapping
    public ResponseEntity<RegulatoryProfileDto> getRegulatoryProfile(@PathVariable UUID orgId,
                                                                     @RequestHeader("X-User-Id") UUID userId) {
        RegulatoryProfileDto profile = organizationService.getRegulatoryProfile(orgId, userId);
        return ResponseEntity.ok(profile);
    }
}