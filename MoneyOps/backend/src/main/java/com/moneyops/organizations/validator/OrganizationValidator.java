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
        if (dto.getPrimaryEmail() != null && !isValidEmail(dto.getPrimaryEmail())) {
            throw new IllegalArgumentException("Invalid email format");
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