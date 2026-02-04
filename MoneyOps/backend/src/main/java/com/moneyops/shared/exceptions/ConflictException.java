// src/main/java/com/moneyops/shared/exceptions/ConflictException.java
package com.moneyops.shared.exceptions;

public class ConflictException extends ApiException {

    public ConflictException(String message) {
        super(message);
    }

    public ConflictException(String resource, Object value) {
        super(resource + " already exists: " + value);
    }
}