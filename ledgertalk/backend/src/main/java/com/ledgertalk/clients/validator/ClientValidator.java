// src/main/java/com/ledgertalk/clients/validator/ClientValidator.java
package com.ledgertalk.clients.validator;

import com.ledgertalk.clients.dto.ClientDto;
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