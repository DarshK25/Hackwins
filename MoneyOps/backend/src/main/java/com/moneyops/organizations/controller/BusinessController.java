// src/main/java/com/moneyops/organizations/controller/BusinessController.java
package com.moneyops.organizations.controller;

import com.moneyops.organizations.dto.BusinessOrganizationDto;
import com.moneyops.organizations.dto.DeleteAccountRequest;
import com.moneyops.organizations.service.OrganizationDeletionService;
import com.moneyops.organizations.service.OrganizationService;
import com.moneyops.shared.dto.ApiResponse;
import com.moneyops.shared.utils.OrgContext;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/org")
@RequiredArgsConstructor
public class BusinessController {

    private final OrganizationService organizationService;
    private final OrganizationDeletionService organizationDeletionService;

    private String resolveUserId(String headerUserId) {
        String currentUserId = OrgContext.getUserId();
        return (currentUserId != null && !currentUserId.isBlank()) ? currentUserId : headerUserId;
    }

    @PostMapping
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> createOrganization(@RequestBody BusinessOrganizationDto dto,
                                                                        @RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto created = organizationService.createOrganization(dto, resolveUserId(userId));
        return ResponseEntity.ok(ApiResponse.success(created));
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> updateOrganization(@PathVariable String id,
                                                                        @RequestBody BusinessOrganizationDto dto,
                                                                        @RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto updated = organizationService.updateOrganization(id, dto, resolveUserId(userId));
        return ResponseEntity.ok(ApiResponse.success(updated));
    }

    @PatchMapping("/{id}")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> partialUpdateOrganization(@PathVariable String id,
                                                                               @RequestBody BusinessOrganizationDto dto,
                                                                               @RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto updated = organizationService.updateOrganization(id, dto, resolveUserId(userId));
        return ResponseEntity.ok(ApiResponse.success(updated));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> getOrganization(@PathVariable String id,
                                                                     @RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto org = organizationService.getOrganizationById(id, resolveUserId(userId));
        return ResponseEntity.ok(ApiResponse.success(org));
    }

    @GetMapping("/my")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> getMyOrganization(@RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto org = organizationService.getMyOrganization(resolveUserId(userId));
        return ResponseEntity.ok(ApiResponse.success(org));
    }

    @GetMapping
    public ResponseEntity<ApiResponse<List<BusinessOrganizationDto>>> getAllOrganizations(@RequestHeader("X-User-Id") String userId) {
        List<BusinessOrganizationDto> orgs = organizationService.getAllOrganizations(resolveUserId(userId));
        return ResponseEntity.ok(ApiResponse.success(orgs));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteOrganization(@PathVariable String id,
                                                   @Valid @RequestBody DeleteAccountRequest request,
                                                   @RequestHeader("X-User-Id") String userId) {
        organizationDeletionService.deleteOrganizationPermanently(id, resolveUserId(userId), request.getTeamActionCode());
        return ResponseEntity.ok(ApiResponse.success("Account deleted permanently", null));
    }
}
