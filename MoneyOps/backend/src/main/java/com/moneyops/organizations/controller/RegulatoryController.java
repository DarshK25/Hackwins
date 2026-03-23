// src/main/java/com/moneyops/organizations/controller/RegulatoryController.java
package com.moneyops.organizations.controller;

import com.moneyops.organizations.dto.RegulatoryProfileDto;
import com.moneyops.organizations.service.OrganizationService;
import com.moneyops.shared.dto.ApiResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/org/{orgId}/regulatory")
@RequiredArgsConstructor
public class RegulatoryController {

    private final OrganizationService organizationService;

    @PostMapping
    public ResponseEntity<ApiResponse<RegulatoryProfileDto>> createRegulatoryProfile(@PathVariable String orgId,
                                                                          @RequestBody RegulatoryProfileDto dto,
                                                                          @RequestHeader("X-User-Id") String userId) {
        RegulatoryProfileDto created = organizationService.createRegulatoryProfile(orgId, dto, userId);
        return ResponseEntity.ok(ApiResponse.success(created));
    }

    @PutMapping
    public ResponseEntity<ApiResponse<RegulatoryProfileDto>> updateRegulatoryProfile(@PathVariable String orgId,
                                                                          @RequestBody RegulatoryProfileDto dto,
                                                                          @RequestHeader("X-User-Id") String userId) {
        RegulatoryProfileDto updated = organizationService.updateRegulatoryProfile(orgId, dto, userId);
        return ResponseEntity.ok(ApiResponse.success(updated));
    }

    @PatchMapping
    public ResponseEntity<ApiResponse<RegulatoryProfileDto>> partialUpdateRegulatoryProfile(@PathVariable String orgId,
                                                                                 @RequestBody RegulatoryProfileDto dto,
                                                                                 @RequestHeader("X-User-Id") String userId) {
        RegulatoryProfileDto updated = organizationService.updateRegulatoryProfile(orgId, dto, userId);
        return ResponseEntity.ok(ApiResponse.success(updated));
    }

    @GetMapping
    public ResponseEntity<ApiResponse<RegulatoryProfileDto>> getRegulatoryProfile(@PathVariable String orgId,
                                                                     @RequestHeader("X-User-Id") String userId) {
        RegulatoryProfileDto profile = organizationService.getRegulatoryProfile(orgId, userId);
        return ResponseEntity.ok(ApiResponse.success(profile));
    }
}