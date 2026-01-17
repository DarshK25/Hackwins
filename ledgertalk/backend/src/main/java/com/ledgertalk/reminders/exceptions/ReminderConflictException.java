package com.ledgertalk.reminders.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.CONFLICT)
public class ReminderConflictException extends RuntimeException {
    public ReminderConflictException(String message) {
        super(message);
    }
}
