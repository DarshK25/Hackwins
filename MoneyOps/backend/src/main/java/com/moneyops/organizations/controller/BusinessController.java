// src/main/java/com/moneyops/organizations/controller/BusinessController.java
package com.moneyops.organizations.controller;

import com.moneyops.organizations.dto.BusinessOrganizationDto;
import com.moneyops.organizations.service.OrganizationService;
import com.moneyops.shared.dto.ApiResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/org")
@RequiredArgsConstructor
public class BusinessController {

    private final OrganizationService organizationService;

    @PostMapping
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> createOrganization(@RequestBody BusinessOrganizationDto dto,
                                                                        @RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto created = organizationService.createOrganization(dto, userId);
        return ResponseEntity.ok(ApiResponse.success(created));
    }

    @PutMapping("/{id}")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> updateOrganization(@PathVariable String id,
                                                                        @RequestBody BusinessOrganizationDto dto,
                                                                        @RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto updated = organizationService.updateOrganization(id, dto, userId);
        return ResponseEntity.ok(ApiResponse.success(updated));
    }

    @PatchMapping("/{id}")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> partialUpdateOrganization(@PathVariable String id,
                                                                               @RequestBody BusinessOrganizationDto dto,
                                                                               @RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto updated = organizationService.updateOrganization(id, dto, userId);
        return ResponseEntity.ok(ApiResponse.success(updated));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> getOrganization(@PathVariable String id,
                                                                     @RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto org = organizationService.getOrganizationById(id, userId);
        return ResponseEntity.ok(ApiResponse.success(org));
    }

    @GetMapping("/my")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> getMyOrganization(@RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto org = organizationService.getMyOrganization(userId);
        return ResponseEntity.ok(ApiResponse.success(org));
    }

    @GetMapping
    public ResponseEntity<ApiResponse<List<BusinessOrganizationDto>>> getAllOrganizations(@RequestHeader("X-User-Id") String userId) {
        List<BusinessOrganizationDto> orgs = organizationService.getAllOrganizations(userId);
        return ResponseEntity.ok(ApiResponse.success(orgs));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteOrganization(@PathVariable String id,
                                                   @RequestHeader("X-User-Id") String userId) {
        organizationService.deleteOrganization(id, userId);
        return ResponseEntity.ok(ApiResponse.success(null));
    }
}