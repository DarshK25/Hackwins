// src/main/java/com/ledgertalk/invoices/exceptions/InvalidInvoiceStateException.java
package com.ledgertalk.invoices.exceptions;

import com.ledgertalk.shared.exceptions.ValidationException;

public class InvalidInvoiceStateException extends ValidationException {

    public InvalidInvoiceStateException(String currentState, String attemptedAction) {
        super("Invalid invoice state transition: " + currentState + " -> " + attemptedAction);
    }
}