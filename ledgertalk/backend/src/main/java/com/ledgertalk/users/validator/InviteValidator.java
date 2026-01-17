// src/main/java/com/ledgertalk/users/validator/InviteValidator.java
package com.ledgertalk.users.validator;

import com.ledgertalk.users.dto.AcceptInviteRequest;
import org.springframework.stereotype.Component;

@Component
public class InviteValidator {

    public void validateAcceptInvite(AcceptInviteRequest request) {
        if (request.getToken() == null || request.getToken().trim().isEmpty()) {
            throw new IllegalArgumentException("Token is required");
        }
        if (request.getPassword() == null || request.getPassword().length() < 8) {
            throw new IllegalArgumentException("Password must be at least 8 characters");
        }
        if (request.getName() == null || request.getName().trim().isEmpty()) {
            throw new IllegalArgumentException("Name is required");
        }
    }
}