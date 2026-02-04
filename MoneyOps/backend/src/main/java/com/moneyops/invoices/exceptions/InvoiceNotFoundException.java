// src/main/java/com/moneyops/invoices/exceptions/InvoiceNotFoundException.java
package com.moneyops.invoices.exceptions;

import com.moneyops.shared.exceptions.NotFoundException;

import java.util.UUID;

public class InvoiceNotFoundException extends NotFoundException {

    public InvoiceNotFoundException(UUID id) {
        super("Invoice", id);
    }
}