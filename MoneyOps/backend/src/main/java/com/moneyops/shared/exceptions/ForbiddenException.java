// src/main/java/com/moneyops/shared/exceptions/ForbiddenException.java
package com.moneyops.shared.exceptions;

public class ForbiddenException extends ApiException {

    public ForbiddenException(String message) {
        super(message);
    }

    public ForbiddenException() {
        super("Access forbidden");
    }
}