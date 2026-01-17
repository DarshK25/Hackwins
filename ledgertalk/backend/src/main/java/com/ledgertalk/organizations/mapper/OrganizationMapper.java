// src/main/java/com/ledgertalk/organizations/mapper/OrganizationMapper.java
package com.ledgertalk.organizations.mapper;

import com.ledgertalk.organizations.dto.BusinessOrganizationDto;
import com.ledgertalk.organizations.dto.RegulatoryProfileDto;
import com.ledgertalk.organizations.entity.BusinessOrganization;
import com.ledgertalk.organizations.entity.RegulatoryProfile;
import org.springframework.stereotype.Component;

@Component
public class OrganizationMapper {

    public BusinessOrganizationDto toDto(BusinessOrganization org) {
        BusinessOrganizationDto dto = new BusinessOrganizationDto();
        dto.setId(org.getId());
        dto.setLegalName(org.getLegalName());
        dto.setTradingName(org.getTradingName());
        dto.setBusinessType(org.getBusinessType() != null ? org.getBusinessType().name() : null);
        dto.setIndustry(org.getIndustry() != null ? org.getIndustry().name() : null);
        dto.setRegistrationDate(org.getRegistrationDate());
        dto.setAnnualTurnoverRange(org.getAnnualTurnoverRange() != null ? org.getAnnualTurnoverRange().name() : null);
        dto.setPrimaryEmail(org.getPrimaryEmail());
        dto.setPrimaryPhone(org.getPrimaryPhone());
        dto.setWebsite(org.getWebsite());
        dto.setEmployeeCount(org.getEmployeeCount());
        dto.setRegisteredAddress(org.getRegisteredAddress());
        dto.setFinancialYearStartMonth(org.getFinancialYearStartMonth() != null ? org.getFinancialYearStartMonth().name() : null);
        dto.setPreferredLanguage(org.getPreferredLanguage());
        dto.setPrimaryActivity(org.getPrimaryActivity());
        dto.setTargetMarket(org.getTargetMarket() != null ? org.getTargetMarket().name() : null);
        dto.setAccountingMethod(org.getAccountingMethod() != null ? org.getAccountingMethod().name() : null);
        return dto;
    }

    public BusinessOrganization toEntity(BusinessOrganizationDto dto) {
        BusinessOrganization org = new BusinessOrganization();
        org.setId(dto.getId());
        org.setLegalName(dto.getLegalName());
        org.setTradingName(dto.getTradingName());
        org.setBusinessType(dto.getBusinessType() != null ? BusinessOrganization.BusinessType.valueOf(dto.getBusinessType()) : null);
        org.setIndustry(dto.getIndustry() != null ? BusinessOrganization.Industry.valueOf(dto.getIndustry()) : null);
        org.setRegistrationDate(dto.getRegistrationDate());
        org.setAnnualTurnoverRange(dto.getAnnualTurnoverRange() != null ? BusinessOrganization.TurnoverRange.valueOf(dto.getAnnualTurnoverRange()) : null);
        org.setPrimaryEmail(dto.getPrimaryEmail());
        org.setPrimaryPhone(dto.getPrimaryPhone());
        org.setWebsite(dto.getWebsite());
        org.setEmployeeCount(dto.getEmployeeCount());
        org.setRegisteredAddress(dto.getRegisteredAddress());
        org.setFinancialYearStartMonth(dto.getFinancialYearStartMonth() != null ? BusinessOrganization.Month.valueOf(dto.getFinancialYearStartMonth()) : null);
        org.setPreferredLanguage(dto.getPreferredLanguage());
        org.setPrimaryActivity(dto.getPrimaryActivity());
        org.setTargetMarket(dto.getTargetMarket() != null ? BusinessOrganization.TargetMarket.valueOf(dto.getTargetMarket()) : null);
        org.setAccountingMethod(dto.getAccountingMethod() != null ? BusinessOrganization.AccountingMethod.valueOf(dto.getAccountingMethod()) : null);
        return org;
    }

    public RegulatoryProfileDto toRegulatoryDto(RegulatoryProfile profile) {
        RegulatoryProfileDto dto = new RegulatoryProfileDto();
        dto.setPanNumber(profile.getPanNumber());
        dto.setStateOfRegistration(profile.getStateOfRegistration());
        dto.setGstRegistered(profile.getGstRegistered());
        dto.setGstNumber(profile.getGstNumber());
        dto.setTanNumber(profile.getTanNumber());
        dto.setCinOrLlpIn(profile.getCinOrLlpIn());
        dto.setMsmeNumber(profile.getMsmeNumber());
        dto.setIecCode(profile.getIecCode());
        return dto;
    }

    public RegulatoryProfile toRegulatoryEntity(RegulatoryProfileDto dto, BusinessOrganization org) {
        RegulatoryProfile profile = new RegulatoryProfile();
        profile.setOrganization(org);
        profile.setPanNumber(dto.getPanNumber());
        profile.setStateOfRegistration(dto.getStateOfRegistration());
        profile.setGstRegistered(dto.getGstRegistered());
        profile.setGstNumber(dto.getGstNumber());
        profile.setTanNumber(dto.getTanNumber());
        profile.setCinOrLlpIn(dto.getCinOrLlpIn());
        profile.setMsmeNumber(dto.getMsmeNumber());
        profile.setIecCode(dto.getIecCode());
        return profile;
    }
}