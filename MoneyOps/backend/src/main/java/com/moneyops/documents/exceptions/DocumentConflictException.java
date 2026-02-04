package com.moneyops.documents.exceptions;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

@ResponseStatus(HttpStatus.CONFLICT)
public class DocumentConflictException extends RuntimeException {
    public DocumentConflictException(String message) {
        super(message);
    }
}
