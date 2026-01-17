package com.ledgertalk.reminders.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.BAD_REQUEST)
public class ReminderRuleViolationException extends RuntimeException {
    public ReminderRuleViolationException(String message) {
        super(message);
    }
}
