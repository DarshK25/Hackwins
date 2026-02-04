// src/main/java/com/moneyops/clients/validator/ClientValidator.java
package com.moneyops.clients.validator;

import com.moneyops.clients.dto.ClientDto;
import org.springframework.stereotype.Component;

@Component
public class ClientValidator {

    public void validate(ClientDto dto) {
        if (dto.getName() == null || dto.getName().trim().isEmpty()) {
            throw new IllegalArgumentException("Name is required");
        }
        if (dto.getEmail() == null || !isValidEmail(dto.getEmail())) {
            throw new IllegalArgumentException("Valid email is required");
        }
        if (dto.getStatus() == null || dto.getStatus().isEmpty()) {
            throw new IllegalArgumentException("Status is required");
        }
    }

    private boolean isValidEmail(String email) {
        return email != null && email.matches("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+$");
    }
}