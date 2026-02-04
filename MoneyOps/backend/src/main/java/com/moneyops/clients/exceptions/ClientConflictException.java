package com.moneyops.clients.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.CONFLICT)
public class ClientConflictException extends RuntimeException {
    public ClientConflictException(String message) {
        super(message);
    }
}
