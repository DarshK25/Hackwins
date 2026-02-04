// src/main/java/com/moneyops/shared/exceptions/ValidationException.java
package com.moneyops.shared.exceptions;

import java.util.List;

public class ValidationException extends ApiException {

    private List<String> errors;

    public ValidationException(String message) {
        super(message);
    }

    public ValidationException(List<String> errors) {
        super("Validation failed");
        this.errors = errors;
    }

    public List<String> getErrors() {
        return errors;
    }
}