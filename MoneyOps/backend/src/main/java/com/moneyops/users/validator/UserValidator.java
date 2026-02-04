// src/main/java/com/moneyops/users/validator/UserValidator.java
package com.moneyops.users.validator;

import com.moneyops.users.dto.UserDto;
import com.moneyops.users.dto.CreateInviteRequest;
import org.springframework.stereotype.Component;

@Component
public class UserValidator {

    public void validate(UserDto dto) {
        if (dto.getName() == null || dto.getName().trim().isEmpty()) {
            throw new IllegalArgumentException("Name is required");
        }
        if (dto.getEmail() == null || !isValidEmail(dto.getEmail())) {
            throw new IllegalArgumentException("Valid email is required");
        }
        if (dto.getRole() == null || dto.getRole().isEmpty()) {
            throw new IllegalArgumentException("Role is required");
        }
        if (dto.getStatus() == null || dto.getStatus().isEmpty()) {
            throw new IllegalArgumentException("Status is required");
        }
    }

    public void validateInvite(CreateInviteRequest request) {
        if (request.getEmail() == null || !isValidEmail(request.getEmail())) {
            throw new IllegalArgumentException("Valid email is required");
        }
        if (request.getRole() == null || request.getRole().isEmpty()) {
            throw new IllegalArgumentException("Role is required");
        }
    }

    private boolean isValidEmail(String email) {
        return email != null && email.matches("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+$");
    }
}