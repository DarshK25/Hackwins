package com.moneyops.organizations.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.BAD_REQUEST)
public class OrganizationInvalidStateException extends RuntimeException {
    public OrganizationInvalidStateException(String message) {
        super(message);
    }
}
