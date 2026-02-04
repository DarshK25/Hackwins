package com.moneyops.transactions.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.BAD_REQUEST)
public class TransactionInvalidStateException extends RuntimeException {
    public TransactionInvalidStateException(String message) {
        super(message);
    }
}
