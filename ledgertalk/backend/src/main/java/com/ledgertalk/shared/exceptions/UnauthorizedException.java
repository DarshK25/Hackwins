// src/main/java/com/ledgertalk/shared/exceptions/UnauthorizedException.java
package com.ledgertalk.shared.exceptions;

public class UnauthorizedException extends ApiException {

    public UnauthorizedException(String message) {
        super(message);
    }

    public UnauthorizedException() {
        super("Unauthorized access");
    }
}