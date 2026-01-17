package com.ledgertalk.organizations.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.CONFLICT)
public class OrganizationConflictException extends RuntimeException {
    public OrganizationConflictException(String message) {
        super(message);
    }
}
