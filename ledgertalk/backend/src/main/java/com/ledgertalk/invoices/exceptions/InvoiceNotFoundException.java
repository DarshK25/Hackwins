// src/main/java/com/ledgertalk/invoices/exceptions/InvoiceNotFoundException.java
package com.ledgertalk.invoices.exceptions;

import com.ledgertalk.shared.exceptions.NotFoundException;

import java.util.UUID;

public class InvoiceNotFoundException extends NotFoundException {

    public InvoiceNotFoundException(UUID id) {
        super("Invoice", id);
    }
}