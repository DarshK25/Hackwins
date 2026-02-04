// src/main/java/com/moneyops/invoices/exceptions/InvalidInvoiceStateException.java
package com.moneyops.invoices.exceptions;

import com.moneyops.shared.exceptions.ValidationException;

public class InvalidInvoiceStateException extends ValidationException {

    public InvalidInvoiceStateException(String currentState, String attemptedAction) {
        super("Invalid invoice state transition: " + currentState + " -> " + attemptedAction);
    }
}