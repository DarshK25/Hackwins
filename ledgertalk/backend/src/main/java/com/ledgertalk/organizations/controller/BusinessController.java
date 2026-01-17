// src/main/java/com/ledgertalk/organizations/controller/BusinessController.java
package com.ledgertalk.organizations.controller;

import com.ledgertalk.organizations.dto.BusinessOrganizationDto;
import com.ledgertalk.organizations.service.OrganizationService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/org")
@RequiredArgsConstructor
public class BusinessController {

    private final OrganizationService organizationService;

    @PostMapping
    public ResponseEntity<BusinessOrganizationDto> createOrganization(@RequestBody BusinessOrganizationDto dto,
                                                                       @RequestHeader("X-User-Id") UUID userId) {
        BusinessOrganizationDto created = organizationService.createOrganization(dto, userId);
        return ResponseEntity.ok(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<BusinessOrganizationDto> updateOrganization(@PathVariable UUID id,
                                                                       @RequestBody BusinessOrganizationDto dto,
                                                                       @RequestHeader("X-User-Id") UUID userId) {
        BusinessOrganizationDto updated = organizationService.updateOrganization(id, dto, userId);
        return ResponseEntity.ok(updated);
    }

    @PatchMapping("/{id}")
    public ResponseEntity<BusinessOrganizationDto> partialUpdateOrganization(@PathVariable UUID id,
                                                                              @RequestBody BusinessOrganizationDto dto,
                                                                              @RequestHeader("X-User-Id") UUID userId) {
        // For partial update, implement field-by-field update if needed
        BusinessOrganizationDto updated = organizationService.updateOrganization(id, dto, userId);
        return ResponseEntity.ok(updated);
    }

    @GetMapping("/{id}")
    public ResponseEntity<BusinessOrganizationDto> getOrganization(@PathVariable UUID id,
                                                                    @RequestHeader("X-User-Id") UUID userId) {
        BusinessOrganizationDto org = organizationService.getOrganizationById(id, userId);
        return ResponseEntity.ok(org);
    }

    @GetMapping("/my")
    public ResponseEntity<BusinessOrganizationDto> getMyOrganization(@RequestHeader("X-User-Id") UUID userId) {
        BusinessOrganizationDto org = organizationService.getMyOrganization(userId);
        return ResponseEntity.ok(org);
    }

    @GetMapping
    public ResponseEntity<List<BusinessOrganizationDto>> getAllOrganizations(@RequestHeader("X-User-Id") UUID userId) {
        List<BusinessOrganizationDto> orgs = organizationService.getAllOrganizations(userId);
        return ResponseEntity.ok(orgs);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteOrganization(@PathVariable UUID id,
                                                   @RequestHeader("X-User-Id") UUID userId) {
        organizationService.deleteOrganization(id, userId);
        return ResponseEntity.noContent().build();
    }
}