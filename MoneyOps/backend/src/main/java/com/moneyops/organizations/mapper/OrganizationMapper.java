package com.moneyops.organizations.mapper;

import com.moneyops.organizations.dto.BusinessOrganizationDto;
import com.moneyops.organizations.dto.RegulatoryProfileDto;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.entity.RegulatoryProfile;
import org.springframework.stereotype.Component;

@Component
public class OrganizationMapper {

    public BusinessOrganizationDto toDto(BusinessOrganization org) {
        if (org == null) return null;
        
        BusinessOrganizationDto dto = new BusinessOrganizationDto();
        dto.setId(org.getId());
        dto.setLegalName(org.getLegalName());
        dto.setTradingName(org.getTradingName());
        dto.setBusinessType(org.getBusinessType());
        dto.setIndustry(org.getIndustry());
        dto.setRegistrationDate(org.getRegistrationDate());
        dto.setAnnualTurnoverRange(org.getAnnualTurnover());
        dto.setPrimaryEmail(org.getPrimaryEmail());
        dto.setPrimaryPhone(org.getPrimaryPhone());
        dto.setWebsite(org.getWebsite());
        dto.setEmployeeCount(org.getEmployeeCount());
        dto.setRegisteredAddress(org.getRegisteredAddress());
        dto.setPincode(org.getPincode());
        dto.setFinancialYearStartMonth(org.getFyStartMonth() != null ? String.valueOf(org.getFyStartMonth()) : null);
        dto.setPreferredLanguage(org.getPreferredLanguage());
        dto.setPrimaryActivity(org.getPrimaryActivity());
        dto.setTargetMarket(org.getTargetMarket());
        dto.setAccountingMethod(org.getAccountingMethod());

        // Mapping regulatory fields from BusinessOrganization entity to DTO
        dto.setPanNumber(org.getPanNumber());
        dto.setStateOfRegistration(org.getStateOfRegistration());
        dto.setGstRegistered(org.getGstRegistered());
        dto.setGstin(org.getGstin());
        dto.setGstFilingFrequency(org.getGstFilingFrequency());
        dto.setTanNumber(org.getTanNumber());
        dto.setCin(org.getCin());
        dto.setLlpin(org.getLlpin());
        dto.setMsmeNumber(org.getMsmeNumber());
        dto.setIecCode(org.getIecCode());
        dto.setProfessionalTaxReg(org.getProfessionalTaxReg());
        
        return dto;
    }

    public BusinessOrganization toEntity(BusinessOrganizationDto dto) {
        if (dto == null) return null;

        BusinessOrganization org = new BusinessOrganization();
        org.setId(dto.getId());
        org.setLegalName(dto.getLegalName());
        org.setTradingName(dto.getTradingName());
        org.setBusinessType(dto.getBusinessType());
        org.setIndustry(dto.getIndustry());
        org.setRegistrationDate(dto.getRegistrationDate());
        org.setAnnualTurnover(dto.getAnnualTurnoverRange());
        org.setPrimaryEmail(dto.getPrimaryEmail());
        org.setPrimaryPhone(dto.getPrimaryPhone());
        org.setWebsite(dto.getWebsite());
        org.setEmployeeCount(dto.getEmployeeCount());
        org.setRegisteredAddress(dto.getRegisteredAddress());
        org.setPincode(dto.getPincode());
        org.setFyStartMonth(dto.getFinancialYearStartMonth() != null ? Integer.valueOf(dto.getFinancialYearStartMonth()) : null);
        org.setPreferredLanguage(dto.getPreferredLanguage());
        org.setPrimaryActivity(dto.getPrimaryActivity());
        org.setTargetMarket(dto.getTargetMarket());
        org.setAccountingMethod(dto.getAccountingMethod());

        // Mapping regulatory fields from DTO to BusinessOrganization entity
        org.setPanNumber(dto.getPanNumber());
        org.setStateOfRegistration(dto.getStateOfRegistration());
        org.setGstRegistered(dto.getGstRegistered());
        org.setGstin(dto.getGstin());
        org.setGstFilingFrequency(dto.getGstFilingFrequency());
        org.setTanNumber(dto.getTanNumber());
        org.setCin(dto.getCin());
        org.setLlpin(dto.getLlpin());
        org.setMsmeNumber(dto.getMsmeNumber());
        org.setIecCode(dto.getIecCode());
        org.setProfessionalTaxReg(dto.getProfessionalTaxReg());

        return org;
    }

    public RegulatoryProfileDto toRegulatoryDto(RegulatoryProfile profile) {
        if (profile == null) return null;
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
        if (dto == null) return null;
        RegulatoryProfile profile = new RegulatoryProfile();
        profile.setOrgId(org.getId());
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