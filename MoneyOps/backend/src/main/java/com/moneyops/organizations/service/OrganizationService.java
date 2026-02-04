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

    // Business Organization operations
    public List<BusinessOrganizationDto> getAllOrganizations(UUID userId) {
        return orgRepository.findAllByCreatedBy(userId).stream()
                .map(mapper::toDto)
                .collect(Collectors.toList());
    }

    public BusinessOrganizationDto getOrganizationById(UUID id, UUID userId) {
        BusinessOrganization org = orgRepository.findByIdAndCreatedBy(id, userId)
                .orElseThrow(() -> new RuntimeException("Organization not found"));
        return mapper.toDto(org);
    }

    public BusinessOrganizationDto getMyOrganization(UUID userId) {
        List<BusinessOrganization> orgs = orgRepository.findAllByCreatedBy(userId);
        if (orgs.isEmpty()) {
            throw new RuntimeException("No organization found for user");
        }
        return mapper.toDto(orgs.get(0)); // Assuming one org per user for now
    }

    public BusinessOrganizationDto createOrganization(BusinessOrganizationDto dto, UUID userId) {
        validator.validate(dto);

        BusinessOrganization org = mapper.toEntity(dto);
        org.setCreatedBy(userId);
        org.setCreatedAt(LocalDateTime.now());
        org.setUpdatedAt(LocalDateTime.now());

        BusinessOrganization saved = orgRepository.save(org);
        return mapper.toDto(saved);
    }

    public BusinessOrganizationDto updateOrganization(UUID id, BusinessOrganizationDto dto, UUID userId) {
        BusinessOrganization existing = orgRepository.findByIdAndCreatedBy(id, userId)
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
        orgRepository.deleteByIdAndCreatedBy(id, userId);
    }

    // Regulatory Profile operations
    public RegulatoryProfileDto getRegulatoryProfile(UUID orgId, UUID userId) {
        // Verify ownership
        orgRepository.findByIdAndCreatedBy(orgId, userId)
                .orElseThrow(() -> new RuntimeException("Organization not found"));

        RegulatoryProfile profile = regulatoryRepository.findByOrganizationId(orgId)
                .orElseThrow(() -> new RuntimeException("Regulatory profile not found"));
        return mapper.toRegulatoryDto(profile);
    }

    public RegulatoryProfileDto createRegulatoryProfile(UUID orgId, RegulatoryProfileDto dto, UUID userId) {
        BusinessOrganization org = orgRepository.findByIdAndCreatedBy(orgId, userId)
                .orElseThrow(() -> new RuntimeException("Organization not found"));

        validator.validateRegulatory(dto);

        RegulatoryProfile profile = mapper.toRegulatoryEntity(dto, org);
        RegulatoryProfile saved = regulatoryRepository.save(profile);
        return mapper.toRegulatoryDto(saved);
    }

    public RegulatoryProfileDto updateRegulatoryProfile(UUID orgId, RegulatoryProfileDto dto, UUID userId) {
        BusinessOrganization org = orgRepository.findByIdAndCreatedBy(orgId, userId)
                .orElseThrow(() -> new RuntimeException("Organization not found"));

        validator.validateRegulatory(dto);

        RegulatoryProfile existing = regulatoryRepository.findByOrganizationId(orgId)
                .orElseThrow(() -> new RuntimeException("Regulatory profile not found"));

        RegulatoryProfile updated = mapper.toRegulatoryEntity(dto, org);
        updated.setId(existing.getId());
        RegulatoryProfile saved = regulatoryRepository.save(updated);
        return mapper.toRegulatoryDto(saved);
    }
}