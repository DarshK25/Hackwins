// src/main/java/com/moneyops/organizations/validator/OrganizationValidator.java
package com.moneyops.organizations.validator;

import com.moneyops.organizations.dto.BusinessOrganizationDto;
import com.moneyops.organizations.dto.RegulatoryProfileDto;
import org.springframework.stereotype.Component;

@Component
public class OrganizationValidator {

    public void validate(BusinessOrganizationDto dto) {
        if (dto.getLegalName() == null || dto.getLegalName().trim().isEmpty()) {
            throw new IllegalArgumentException("Legal name is required");
        }
        if (dto.getBusinessType() == null || dto.getBusinessType().trim().isEmpty()) {
            throw new IllegalArgumentException("Business type is required");
        }
        if (dto.getIndustry() == null || dto.getIndustry().trim().isEmpty()) {
            throw new IllegalArgumentException("Industry is required");
        }
        if (dto.getPrimaryEmail() == null || dto.getPrimaryEmail().trim().isEmpty()) {
            throw new IllegalArgumentException("Primary email is required");
        }
        if (dto.getPrimaryPhone() == null || dto.getPrimaryPhone().trim().isEmpty()) {
            throw new IllegalArgumentException("Primary phone is required");
        }
        if (dto.getPanNumber() == null || dto.getPanNumber().trim().isEmpty()) {
            throw new IllegalArgumentException("PAN number is required");
        }
        if (dto.getPrimaryActivity() == null || dto.getPrimaryActivity().trim().isEmpty()) {
            throw new IllegalArgumentException("Primary activity is required");
        }
        if (dto.getTargetMarket() == null || dto.getTargetMarket().trim().isEmpty()) {
            throw new IllegalArgumentException("Target market is required");
        }
        if (dto.getPrimaryEmail() != null && !isValidEmail(dto.getPrimaryEmail())) {
            throw new IllegalArgumentException("Invalid email format");
        }
        if (dto.getPanNumber() != null && !isValidPan(dto.getPanNumber())) {
            throw new IllegalArgumentException("Invalid PAN number format");
        }
        if (Boolean.TRUE.equals(dto.getGstRegistered())) {
            if (dto.getGstin() == null || dto.getGstin().trim().isEmpty()) {
                throw new IllegalArgumentException("GSTIN is required when GST is enabled");
            }
            if (dto.getGstFilingFrequency() == null || dto.getGstFilingFrequency().trim().isEmpty()) {
                throw new IllegalArgumentException("GST filing frequency is required when GST is enabled");
            }
        }
        if (dto.getGstin() != null && !dto.getGstin().trim().isEmpty() && !isValidGst(dto.getGstin())) {
            throw new IllegalArgumentException("Invalid GST number format");
        }
        if (dto.getEmployeeCount() != null && dto.getEmployeeCount() < 0) {
            throw new IllegalArgumentException("Employee count cannot be negative");
        }
    }

    public void validateRegulatory(RegulatoryProfileDto dto) {
        if (dto.getPanNumber() != null && !isValidPan(dto.getPanNumber())) {
            throw new IllegalArgumentException("Invalid PAN number format");
        }
        if (dto.getGstNumber() != null && !isValidGst(dto.getGstNumber())) {
            throw new IllegalArgumentException("Invalid GST number format");
        }
    }

    private boolean isValidEmail(String email) {
        return email != null && email.matches("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+$");
    }

    private boolean isValidPan(String pan) {
        return pan != null && pan.matches("[A-Z]{5}[0-9]{4}[A-Z]{1}");
    }

    private boolean isValidGst(String gst) {
        return gst != null && gst.matches("\\d{2}[A-Z]{5}\\d{4}[A-Z]{1}[A-Z\\d]{1}[Z]{1}[A-Z\\d]{1}");
    }
}
