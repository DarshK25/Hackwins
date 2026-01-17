// src/main/java/com/ledgertalk/shared/exceptions/ApiException.java
package com.ledgertalk.shared.exceptions;

public class ApiException extends RuntimeException {

    public ApiException(String message) {
        super(message);
    }

    public ApiException(String message, Throwable cause) {
        super(message, cause);
    }
}