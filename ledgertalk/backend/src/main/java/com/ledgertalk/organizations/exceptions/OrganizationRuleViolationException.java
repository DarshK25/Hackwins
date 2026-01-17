package com.ledgertalk.organizations.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.BAD_REQUEST)
public class OrganizationRuleViolationException extends RuntimeException {
    public OrganizationRuleViolationException(String message) {
        super(message);
    }
}
