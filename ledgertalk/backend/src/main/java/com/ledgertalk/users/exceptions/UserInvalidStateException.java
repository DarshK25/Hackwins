package com.ledgertalk.users.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.BAD_REQUEST)
public class UserInvalidStateException extends RuntimeException {
    public UserInvalidStateException(String message) {
        super(message);
    }
}
