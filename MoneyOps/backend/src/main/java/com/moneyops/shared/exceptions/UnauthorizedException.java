// src/main/java/com/moneyops/shared/exceptions/UnauthorizedException.java
package com.moneyops.shared.exceptions;

public class UnauthorizedException extends ApiException {

    public UnauthorizedException(String message) {
        super(message);
    }

    public UnauthorizedException() {
        super("Unauthorized access");
    }
}