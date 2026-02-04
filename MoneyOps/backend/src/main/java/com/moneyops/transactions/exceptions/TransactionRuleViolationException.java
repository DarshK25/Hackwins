package com.moneyops.transactions.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.BAD_REQUEST)
public class TransactionRuleViolationException extends RuntimeException {
    public TransactionRuleViolationException(String message) {
        super(message);
    }
}
