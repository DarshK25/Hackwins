// src/main/java/com/moneyops/shared/exceptions/ApiException.java
package com.moneyops.shared.exceptions;

public class ApiException extends RuntimeException {

    public ApiException(String message) {
        super(message);
    }

    public ApiException(String message, Throwable cause) {
        super(message, cause);
    }
}