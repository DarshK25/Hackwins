// src/main/java/com/moneyops/shared/exceptions/BusinessRuleException.java
package com.moneyops.shared.exceptions;

public class BusinessRuleException extends ApiException {

    public BusinessRuleException(String message) {
        super(message);
    }

    public BusinessRuleException(String rule, String details) {
        super("Business rule violation: " + rule + " - " + details);
    }
}