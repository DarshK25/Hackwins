// src/main/java/com/moneyops/clients/exceptions/ClientNotFoundException.java
package com.moneyops.clients.exceptions;

import com.moneyops.shared.exceptions.NotFoundException;

import java.util.UUID;

public class ClientNotFoundException extends NotFoundException {

    public ClientNotFoundException(UUID id) {
        super("Client", id);
    }
}