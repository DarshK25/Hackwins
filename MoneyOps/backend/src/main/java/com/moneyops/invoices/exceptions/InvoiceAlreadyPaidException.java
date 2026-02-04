// src/main/java/com/moneyops/invoices/exceptions/InvoiceAlreadyPaidException.java
package com.moneyops.invoices.exceptions;

import com.moneyops.shared.exceptions.BusinessRuleException;

import java.util.UUID;

public class InvoiceAlreadyPaidException extends BusinessRuleException {

    public InvoiceAlreadyPaidException(UUID id) {
        super("Invoice already paid", "Cannot modify paid invoice: " + id);
    }
}