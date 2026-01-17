package com.ledgertalk.invoices.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.BAD_REQUEST)
public class InvoiceRuleViolationException extends RuntimeException {
    public InvoiceRuleViolationException(String message) {
        super(message);
    }
}
