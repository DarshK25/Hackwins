// src/main/java/com/ledgertalk/invoices/exceptions/InvoiceAlreadyPaidException.java
package com.ledgertalk.invoices.exceptions;

import com.ledgertalk.shared.exceptions.BusinessRuleException;

import java.util.UUID;

public class InvoiceAlreadyPaidException extends BusinessRuleException {

    public InvoiceAlreadyPaidException(UUID id) {
        super("Invoice already paid", "Cannot modify paid invoice: " + id);
    }
}