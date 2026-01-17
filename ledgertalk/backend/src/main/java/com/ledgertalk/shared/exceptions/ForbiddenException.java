// src/main/java/com/ledgertalk/shared/exceptions/ForbiddenException.java
package com.ledgertalk.shared.exceptions;

public class ForbiddenException extends ApiException {

    public ForbiddenException(String message) {
        super(message);
    }

    public ForbiddenException() {
        super("Access forbidden");
    }
}