package com.moneyops.clients.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.BAD_REQUEST)
public class ClientRuleViolationException extends RuntimeException {
    public ClientRuleViolationException(String message) {
        super(message);
    }
}
