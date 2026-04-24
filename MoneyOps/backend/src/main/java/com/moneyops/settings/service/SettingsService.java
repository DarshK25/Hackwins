package com.moneyops.settings.service;

import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.mapper.OrganizationMapper;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.organizations.validator.OrganizationValidator;
import com.moneyops.settings.dto.*;
import com.moneyops.settings.entity.UserSettings;
import com.moneyops.settings.repository.UserSettingsRepository;
import com.moneyops.shared.utils.OrgContext;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional
public class SettingsService {

    private final UserSettingsRepository userSettingsRepository;
    private final UserRepository userRepository;
    private final BusinessOrganizationRepository orgRepository;
    private final OrganizationMapper mapper;
    private final OrganizationValidator validator;

    public SettingsResponseDto getSettings() {
        String userId = OrgContext.getUserId();
        String orgId = OrgContext.getOrgId();

        if (userId == null || userId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "User context is missing");
        }
        if (orgId == null || orgId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Organization context is missing");
        }

        User user = userRepository.findByIdAndOrgIdAndDeletedAtIsNull(userId, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));

        BusinessOrganization org = orgRepository.findByIdAndDeletedAtIsNull(orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Organization not found"));

        UserSettings userSettings = userSettingsRepository.findByOrgIdAndUserId(orgId, userId)
                .orElse(UserSettings.builder().orgId(orgId).userId(userId).build());

        SettingsResponseDto response = new SettingsResponseDto();
        response.setProfile(toProfileSettingsDto(user, userSettings));
        response.setBusiness(toBusinessSettingsDto(org));
        response.setNotifications(toNotificationSettingsDto(userSettings));
        response.setSecurity(toSecuritySettingsDto(org));
        response.setPermissions(toPermissionsDto(user, org));
        return response;
    }

    public SettingsResponseDto updateSettings(SettingsUpdateRequestDto request) {
        String section = request.getSection();
        if (section == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Section is required");
        }

        return switch (section) {
            case "profile" -> updateProfile(request.getProfile());
            case "business" -> updateBusiness(request.getBusiness());
            case "notifications" -> updateNotifications(request.getNotifications());
            default -> throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Invalid section: " + section);
        };
    }

    private SettingsResponseDto updateProfile(ProfileSettingsDto profile) {
        if (profile == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Profile data is required");
        }

        String userId = OrgContext.getUserId();
        String orgId = OrgContext.getOrgId();

        User user = userRepository.findByIdAndOrgIdAndDeletedAtIsNull(userId, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));

        UserSettings userSettings = userSettingsRepository.findByOrgIdAndUserId(orgId, userId)
                .orElse(UserSettings.builder().orgId(orgId).userId(userId).build());

        userSettings.setFirstName(profile.getFirstName());
        userSettings.setLastName(profile.getLastName());
        userSettings.setProfessionalTitle(profile.getProfessionalTitle());
        userSettings.setPhone(profile.getPhone());
        userSettingsRepository.save(userSettings);

        String fullName = List.of(profile.getFirstName(), profile.getLastName()).stream()
                .filter(s -> s != null && !s.isBlank())
                .reduce((a, b) -> a + " " + b)
                .orElse(null);
        user.setName(fullName);
        user.setPhone(profile.getPhone());
        userRepository.save(user);

        return getSettings();
    }

    private SettingsResponseDto updateBusiness(BusinessSettingsDto business) {
        if (business == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Business data is required");
        }

        String userId = OrgContext.getUserId();
        String orgId = OrgContext.getOrgId();

        User user = userRepository.findByIdAndOrgIdAndDeletedAtIsNull(userId, orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));

        if (user.getRole() != User.Role.OWNER) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Only owner can update business settings");
        }

        BusinessOrganization org = orgRepository.findByIdAndDeletedAtIsNull(orgId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Organization not found"));

        validator.validate(toBusinessOrgDto(business));

        mergeBusinessOrganization(org, business);
        orgRepository.save(org);

        return getSettings();
    }

    private SettingsResponseDto updateNotifications(NotificationSettingsDto notifications) {
        if (notifications == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Notification data is required");
        }

        String userId = OrgContext.getUserId();
        String orgId = OrgContext.getOrgId();

        UserSettings userSettings = userSettingsRepository.findByOrgIdAndUserId(orgId, userId)
                .orElse(UserSettings.builder().orgId(orgId).userId(userId).build());

        userSettings.setInvoiceDue(notifications.isInvoiceDue());
        userSettings.setPaymentReceived(notifications.isPaymentReceived());
        userSettings.setClientUpdates(notifications.isClientUpdates());
        userSettings.setWeeklyReport(notifications.isWeeklyReport());
        userSettings.setSystemAlerts(notifications.isSystemAlerts());
        userSettingsRepository.save(userSettings);

        return getSettings();
    }

    private ProfileSettingsDto toProfileSettingsDto(User user, UserSettings userSettings) {
        ProfileSettingsDto dto = new ProfileSettingsDto();
        dto.setFirstName(userSettings.getFirstName() != null ? userSettings.getFirstName() : (user.getName() != null && user.getName().contains(" ") ? user.getName().substring(0, user.getName().indexOf(" ")) : user.getName()));
        dto.setLastName(userSettings.getLastName() != null ? userSettings.getLastName() : (user.getName() != null && user.getName().contains(" ") ? user.getName().substring(user.getName().indexOf(" ") + 1) : null));
        dto.setEmail(user.getEmail());
        dto.setPhone(userSettings.getPhone() != null ? userSettings.getPhone() : user.getPhone());
        dto.setProfessionalTitle(userSettings.getProfessionalTitle());
        return dto;
    }

    private BusinessSettingsDto toBusinessSettingsDto(BusinessOrganization org) {
        BusinessSettingsDto dto = new BusinessSettingsDto();
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
        dto.setPrimaryActivity(org.getPrimaryActivity());
        dto.setTargetMarket(org.getTargetMarket());
        dto.setKeyProducts(org.getKeyProducts());
        dto.setCurrentChallenges(org.getCurrentChallenges());
        dto.setAccountingMethod(org.getAccountingMethod());
        dto.setFinancialYearStartMonth(org.getFyStartMonth() != null ? String.valueOf(org.getFyStartMonth()) : null);
        dto.setPreferredLanguage(org.getPreferredLanguage());
        dto.setCurrency(org.getCurrency() != null ? org.getCurrency() : "INR");
        return dto;
    }

    private NotificationSettingsDto toNotificationSettingsDto(UserSettings userSettings) {
        NotificationSettingsDto dto = new NotificationSettingsDto();
        dto.setInvoiceDue(userSettings.isInvoiceDue());
        dto.setPaymentReceived(userSettings.isPaymentReceived());
        dto.setClientUpdates(userSettings.isClientUpdates());
        dto.setWeeklyReport(userSettings.isWeeklyReport());
        dto.setSystemAlerts(userSettings.isSystemAlerts());
        return dto;
    }

    private SecuritySettingsDto toSecuritySettingsDto(BusinessOrganization org) {
        SecuritySettingsDto dto = new SecuritySettingsDto();
        dto.setClerkManagedAuth(true);
        dto.setTeamSecurityCodeConfigured(org.getTeamActionCodeHash() != null && !org.getTeamActionCodeHash().isBlank());
        dto.setDeleteRequiresTeamActionCode(true);
        return dto;
    }

    private SettingsPermissionsDto toPermissionsDto(User user, BusinessOrganization org) {
        SettingsPermissionsDto dto = new SettingsPermissionsDto();
        dto.setCanEditBusiness(user.getRole() == User.Role.OWNER);
        dto.setCanDeleteAccount(user.getRole() == User.Role.OWNER);
        return dto;
    }

    private com.moneyops.organizations.dto.BusinessOrganizationDto toBusinessOrgDto(BusinessSettingsDto dto) {
        com.moneyops.organizations.dto.BusinessOrganizationDto orgDto = new com.moneyops.organizations.dto.BusinessOrganizationDto();
        orgDto.setId(dto.getId());
        orgDto.setLegalName(dto.getLegalName());
        orgDto.setTradingName(dto.getTradingName());
        orgDto.setBusinessType(dto.getBusinessType());
        orgDto.setIndustry(dto.getIndustry());
        orgDto.setRegistrationDate(dto.getRegistrationDate());
        orgDto.setAnnualTurnoverRange(dto.getAnnualTurnoverRange());
        orgDto.setPrimaryEmail(dto.getPrimaryEmail());
        orgDto.setPrimaryPhone(dto.getPrimaryPhone());
        orgDto.setWebsite(dto.getWebsite());
        orgDto.setEmployeeCount(dto.getEmployeeCount());
        orgDto.setRegisteredAddress(dto.getRegisteredAddress());
        orgDto.setPincode(dto.getPincode());
        orgDto.setPanNumber(dto.getPanNumber());
        orgDto.setStateOfRegistration(dto.getStateOfRegistration());
        orgDto.setGstRegistered(dto.getGstRegistered());
        orgDto.setGstin(dto.getGstin());
        orgDto.setGstFilingFrequency(dto.getGstFilingFrequency());
        orgDto.setTanNumber(dto.getTanNumber());
        orgDto.setCin(dto.getCin());
        orgDto.setLlpin(dto.getLlpin());
        orgDto.setMsmeNumber(dto.getMsmeNumber());
        orgDto.setIecCode(dto.getIecCode());
        orgDto.setProfessionalTaxReg(dto.getProfessionalTaxReg());
        orgDto.setPrimaryActivity(dto.getPrimaryActivity());
        orgDto.setTargetMarket(dto.getTargetMarket());
        orgDto.setKeyProducts(dto.getKeyProducts());
        orgDto.setCurrentChallenges(dto.getCurrentChallenges());
        orgDto.setAccountingMethod(dto.getAccountingMethod());
        orgDto.setFinancialYearStartMonth(dto.getFinancialYearStartMonth());
        orgDto.setPreferredLanguage(dto.getPreferredLanguage());
        orgDto.setCurrency(dto.getCurrency());
        return orgDto;
    }

    private void mergeBusinessOrganization(BusinessOrganization existing, BusinessSettingsDto dto) {
        existing.setLegalName(dto.getLegalName());
        existing.setTradingName(dto.getTradingName());
        existing.setBusinessType(dto.getBusinessType());
        existing.setIndustry(dto.getIndustry());
        existing.setRegistrationDate(dto.getRegistrationDate());
        existing.setAnnualTurnover(dto.getAnnualTurnoverRange());
        existing.setPrimaryEmail(dto.getPrimaryEmail());
        existing.setPrimaryPhone(dto.getPrimaryPhone());
        existing.setWebsite(dto.getWebsite());
        existing.setEmployeeCount(dto.getEmployeeCount());
        existing.setRegisteredAddress(dto.getRegisteredAddress());
        existing.setPincode(dto.getPincode());
        existing.setPreferredLanguage(dto.getPreferredLanguage());
        existing.setPrimaryActivity(dto.getPrimaryActivity());
        existing.setTargetMarket(dto.getTargetMarket());
        existing.setAccountingMethod(dto.getAccountingMethod());
        existing.setKeyProducts(dto.getKeyProducts());
        existing.setCurrentChallenges(dto.getCurrentChallenges());
        existing.setPanNumber(dto.getPanNumber());
        existing.setStateOfRegistration(dto.getStateOfRegistration());
        existing.setGstRegistered(dto.getGstRegistered());
        existing.setGstin(dto.getGstin());
        existing.setGstFilingFrequency(dto.getGstFilingFrequency());
        existing.setTanNumber(dto.getTanNumber());
        existing.setCin(dto.getCin());
        existing.setLlpin(dto.getLlpin());
        existing.setMsmeNumber(dto.getMsmeNumber());
        existing.setIecCode(dto.getIecCode());
        existing.setProfessionalTaxReg(dto.getProfessionalTaxReg());
        existing.setCurrency(dto.getCurrency() != null ? dto.getCurrency() : "INR");

        if (dto.getFinancialYearStartMonth() != null && !dto.getFinancialYearStartMonth().isBlank()) {
            existing.setFyStartMonth(Integer.valueOf(dto.getFinancialYearStartMonth()));
        } else {
            existing.setFyStartMonth(null);
        }
    }
}
