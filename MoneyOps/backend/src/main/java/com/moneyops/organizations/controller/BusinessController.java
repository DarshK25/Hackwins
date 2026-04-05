// src/main/java/com/moneyops/organizations/controller/BusinessController.java
package com.moneyops.organizations.controller;

import com.moneyops.organizations.dto.BusinessOrganizationDto;
import com.moneyops.organizations.service.OrganizationService;
import com.moneyops.shared.dto.ApiResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.regex.Pattern;

@RestController
@RequestMapping("/api/org")
@RequiredArgsConstructor
public class BusinessController {

    private final OrganizationService organizationService;

    private static final Pattern GSTIN_PATTERN = Pattern.compile(
            "^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    );

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

    @PostMapping("/verify/basic")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> verifyBasic(
            @RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto org = organizationService.getMyOrganization(userId);

        if (org.getLegalName() == null || org.getLegalName().isBlank()) {
            return ResponseEntity.badRequest().body(
                    ApiResponse.error("Legal name is required for BASIC verification"));
        }
        if (org.getPrimaryPhone() == null || org.getPrimaryPhone().isBlank()) {
            return ResponseEntity.badRequest().body(
                    ApiResponse.error("Primary phone is required for BASIC verification"));
        }
        if (org.getIndustry() == null || org.getIndustry().isBlank()) {
            return ResponseEntity.badRequest().body(
                    ApiResponse.error("Industry is required for BASIC verification"));
        }

        BusinessOrganizationDto updated = organizationService.updateVerificationTier(
                org.getId(), userId, "BASIC");
        return ResponseEntity.ok(ApiResponse.success("Basic verification complete", updated));
    }

    @PostMapping("/verify/gst-certificate")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> verifyGstCertificate(
            @RequestParam("file") MultipartFile file,
            @RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto org = organizationService.getMyOrganization(userId);

        if (org.getGstin() == null || org.getGstin().isBlank()) {
            return ResponseEntity.badRequest().body(
                    ApiResponse.error("GSTIN is required before uploading the certificate"));
        }

        if (!GSTIN_PATTERN.matcher(org.getGstin().toUpperCase()).matches()) {
            return ResponseEntity.badRequest().body(
                    ApiResponse.error("Invalid GSTIN format. Expected 15-character GST Identification Number."));
        }

        if (file == null || file.isEmpty()) {
            return ResponseEntity.badRequest().body(
                    ApiResponse.error("Certificate file is required"));
        }

        String contentType = file.getContentType();
        if (contentType == null || (!contentType.equals("application/pdf") && !contentType.startsWith("image/"))) {
            return ResponseEntity.badRequest().body(
                    ApiResponse.error("Certificate must be a PDF or image file (JPG/PNG)"));
        }

        BusinessOrganizationDto updated = organizationService.updateVerificationTier(
                org.getId(), userId, "GST_VERIFIED");
        return ResponseEntity.ok(ApiResponse.success("GST certificate uploaded and verified", updated));
    }

    @GetMapping("/verify/status")
    public ResponseEntity<ApiResponse<BusinessOrganizationDto>> getVerificationStatus(
            @RequestHeader("X-User-Id") String userId) {
        BusinessOrganizationDto org = organizationService.getVerificationTier(
                organizationService.getMyOrganization(userId).getId(), userId);
        return ResponseEntity.ok(ApiResponse.success(org));
    }
}