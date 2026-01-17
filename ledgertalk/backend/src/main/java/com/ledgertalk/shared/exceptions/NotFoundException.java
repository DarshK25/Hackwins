// src/main/java/com/ledgertalk/shared/exceptions/NotFoundException.java
package com.ledgertalk.shared.exceptions;

public class NotFoundException extends ApiException {

    public NotFoundException(String resource, Object id) {
        super(resource + " not found with id: " + id);
    }

    public NotFoundException(String message) {
        super(message);
    }
}