package com.ledgertalk.reminders.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.BAD_REQUEST)
public class ReminderInvalidStateException extends RuntimeException {
    public ReminderInvalidStateException(String message) {
        super(message);
    }
}
