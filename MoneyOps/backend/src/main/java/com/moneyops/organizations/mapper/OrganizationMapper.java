package com.moneyops.organizations.mapper;

import com.moneyops.organizations.dto.BusinessOrganizationDto;
import com.moneyops.organizations.dto.RegulatoryProfileDto;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.entity.RegulatoryProfile;
import org.springframework.stereotype.Component;

@Component
public class OrganizationMapper {

    public BusinessOrganizationDto toDto(BusinessOrganization org) {
        BusinessOrganizationDto dto = new BusinessOrganizationDto();
        dto.setId(org.getId());
        dto.setLegalName(org.getLegalName());
        dto.setTradingName(org.getTradingName());
        dto.setBusinessType(org.getBusinessType());       // plain String now
        dto.setIndustry(org.getIndustry());
        dto.setRegistrationDate(org.getRegistrationDate());
        dto.setAnnualTurnoverRange(org.getAnnualTurnover());
        dto.setPrimaryEmail(org.getPrimaryEmail());
        dto.setPrimaryPhone(org.getPrimaryPhone());
        dto.setWebsite(org.getWebsite());
        dto.setEmployeeCount(org.getEmployeeCount());
        dto.setRegisteredAddress(org.getRegisteredAddress());
        dto.setFinancialYearStartMonth(org.getFyStartMonth() != null ? String.valueOf(org.getFyStartMonth()) : null);
        dto.setPreferredLanguage(org.getPreferredLanguage());
        dto.setPrimaryActivity(org.getPrimaryActivity());
        dto.setTargetMarket(org.getTargetMarket());
        dto.setAccountingMethod(org.getAccountingMethod());
        return dto;
    }

    public BusinessOrganization toEntity(BusinessOrganizationDto dto) {
        BusinessOrganization org = new BusinessOrganization();
        org.setId(dto.getId());
        org.setLegalName(dto.getLegalName());
        org.setTradingName(dto.getTradingName());
        org.setBusinessType(dto.getBusinessType());       // plain String now
        org.setIndustry(dto.getIndustry());
        org.setRegistrationDate(dto.getRegistrationDate());
        org.setAnnualTurnover(dto.getAnnualTurnoverRange());
        org.setPrimaryEmail(dto.getPrimaryEmail());
        org.setPrimaryPhone(dto.getPrimaryPhone());
        org.setWebsite(dto.getWebsite());
        org.setEmployeeCount(dto.getEmployeeCount());
        org.setRegisteredAddress(dto.getRegisteredAddress());
        org.setFyStartMonth(dto.getFinancialYearStartMonth() != null ? Integer.valueOf(dto.getFinancialYearStartMonth()) : null);
        org.setPreferredLanguage(dto.getPreferredLanguage());
        org.setPrimaryActivity(dto.getPrimaryActivity());
        org.setTargetMarket(dto.getTargetMarket());
        org.setAccountingMethod(dto.getAccountingMethod());
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
        profile.setOrgId(org.getId());   // use orgId reference (not @OneToOne anymore)
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