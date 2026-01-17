// src/main/java/com/ledgertalk/shared/exceptions/ConflictException.java
package com.ledgertalk.shared.exceptions;

public class ConflictException extends ApiException {

    public ConflictException(String message) {
        super(message);
    }

    public ConflictException(String resource, Object value) {
        super(resource + " already exists: " + value);
    }
}