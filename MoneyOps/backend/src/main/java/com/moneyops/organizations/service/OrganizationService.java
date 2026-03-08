// src/main/java/com/moneyops/organizations/service/OrganizationService.java
package com.moneyops.organizations.service;

import com.moneyops.organizations.dto.BusinessOrganizationDto;
import com.moneyops.organizations.dto.RegulatoryProfileDto;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.entity.RegulatoryProfile;
import com.moneyops.organizations.mapper.OrganizationMapper;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.organizations.repository.RegulatoryProfileRepository;
import com.moneyops.organizations.validator.OrganizationValidator;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional
public class OrganizationService {

    private final BusinessOrganizationRepository orgRepository;
    private final RegulatoryProfileRepository regulatoryRepository;
    private final OrganizationMapper mapper;
    private final OrganizationValidator validator;
    private final UserRepository userRepository;

    // Helper to verify user belongs to org
    private void verifyAccess(UUID orgId, UUID userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));
        
        // Allow access if they are the creator OR if their profile orgId matches
        if (user.getOrgId() != null && user.getOrgId().equals(orgId)) {
            return;
        }

        BusinessOrganization org = orgRepository.findById(orgId)
                .orElseThrow(() -> new RuntimeException("Organization not found"));
        
        if (org.getCreatedBy() != null && org.getCreatedBy().equals(userId)) {
            return;
        }

        throw new RuntimeException("Access denied: You do not belong to this organization");
    }

    // Business Organization operations
    public List<BusinessOrganizationDto> getAllOrganizations(UUID userId) {
        // Return orgs created by user or orgs user belongs to
        User user = userRepository.findById(userId).orElse(null);
        if (user != null && user.getOrgId() != null) {
            return orgRepository.findById(user.getOrgId()).stream()
                    .map(mapper::toDto)
                    .collect(Collectors.toList());
        }
        return orgRepository.findAllByCreatedBy(userId).stream()
                .map(mapper::toDto)
                .collect(Collectors.toList());
    }

    public BusinessOrganizationDto getOrganizationById(UUID id, UUID userId) {
        verifyAccess(id, userId);
        BusinessOrganization org = orgRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Organization not found"));
        return mapper.toDto(org);
    }

    public BusinessOrganizationDto getMyOrganization(UUID userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new RuntimeException("User not found"));
        
        UUID orgId = user.getOrgId();
        if (orgId == null) {
            List<BusinessOrganization> createdOrgs = orgRepository.findAllByCreatedBy(userId);
            if (createdOrgs.isEmpty()) throw new RuntimeException("No organization found for user");
            return mapper.toDto(createdOrgs.get(0));
        }
        
        BusinessOrganization org = orgRepository.findById(orgId)
                .orElseThrow(() -> new RuntimeException("Organization not found"));
        return mapper.toDto(org);
    }

    public BusinessOrganizationDto createOrganization(BusinessOrganizationDto dto, UUID userId) {
        validator.validate(dto);

        BusinessOrganization org = mapper.toEntity(dto);
        org.setCreatedBy(userId);
        org.setCreatedAt(LocalDateTime.now());
        org.setUpdatedAt(LocalDateTime.now());

        BusinessOrganization saved = orgRepository.save(org);
        
        // Update user's orgId if not set
        userRepository.findById(userId).ifPresent(u -> {
            if (u.getOrgId() == null) {
                u.setOrgId(saved.getId());
                u.setRole(User.Role.OWNER);
                userRepository.save(u);
            }
        });

        return mapper.toDto(saved);
    }

    public BusinessOrganizationDto updateOrganization(UUID id, BusinessOrganizationDto dto, UUID userId) {
        verifyAccess(id, userId);
        BusinessOrganization existing = orgRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Organization not found"));

        validator.validate(dto);

        BusinessOrganization updated = mapper.toEntity(dto);
        updated.setId(id);
        updated.setCreatedAt(existing.getCreatedAt());
        updated.setCreatedBy(existing.getCreatedBy());
        updated.setUpdatedAt(LocalDateTime.now());

        BusinessOrganization saved = orgRepository.save(updated);
        return mapper.toDto(saved);
    }

    public void deleteOrganization(UUID id, UUID userId) {
        verifyAccess(id, userId);
        orgRepository.deleteById(id);
    }

    // Regulatory Profile operations - Keep for legacy/compat but regulatory info is now in BusinessOrganization
    public RegulatoryProfileDto getRegulatoryProfile(UUID orgId, UUID userId) {
        verifyAccess(orgId, userId);
        RegulatoryProfile profile = regulatoryRepository.findByOrgId(orgId)
                .orElseGet(() -> {
                    // Fallback to BusinessOrganization fields if RegulatoryProfile doesn't exist
                    BusinessOrganization org = orgRepository.findById(orgId).orElseThrow();
                    RegulatoryProfile p = new RegulatoryProfile();
                    p.setOrgId(orgId);
                    p.setPanNumber(org.getPanNumber());
                    p.setGstNumber(org.getGstin());
                    return p;
                });
        return mapper.toRegulatoryDto(profile);
    }

    public RegulatoryProfileDto createRegulatoryProfile(UUID orgId, RegulatoryProfileDto dto, UUID userId) {
        verifyAccess(orgId, userId);
        BusinessOrganization org = orgRepository.findById(orgId)
                .orElseThrow(() -> new RuntimeException("Organization not found"));

        validator.validateRegulatory(dto);

        RegulatoryProfile profile = mapper.toRegulatoryEntity(dto, org);
        RegulatoryProfile saved = regulatoryRepository.save(profile);

        // Also sync to BusinessOrganization for new consolidated storage
        org.setPanNumber(dto.getPanNumber());
        org.setGstRegistered(dto.getGstRegistered());
        org.setGstin(dto.getGstNumber());
        orgRepository.save(org);

        return mapper.toRegulatoryDto(saved);
    }

    public RegulatoryProfileDto updateRegulatoryProfile(UUID orgId, RegulatoryProfileDto dto, UUID userId) {
        verifyAccess(orgId, userId);
        BusinessOrganization org = orgRepository.findById(orgId)
                .orElseThrow(() -> new RuntimeException("Organization not found"));

        validator.validateRegulatory(dto);

        RegulatoryProfile existing = regulatoryRepository.findByOrgId(orgId)
                .orElse(new RegulatoryProfile());

        RegulatoryProfile updated = mapper.toRegulatoryEntity(dto, org);
        if (existing.getId() != null) {
            updated.setId(existing.getId());
        }

        RegulatoryProfile saved = regulatoryRepository.save(updated);

        // Sync back to BusinessOrganization
        org.setPanNumber(dto.getPanNumber());
        org.setGstRegistered(dto.getGstRegistered());
        org.setGstin(dto.getGstNumber());
        orgRepository.save(org);

        return mapper.toRegulatoryDto(saved);
    }
}