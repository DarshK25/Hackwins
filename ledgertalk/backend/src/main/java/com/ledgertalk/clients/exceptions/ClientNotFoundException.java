// src/main/java/com/ledgertalk/clients/exceptions/ClientNotFoundException.java
package com.ledgertalk.clients.exceptions;

import com.ledgertalk.shared.exceptions.NotFoundException;

import java.util.UUID;

public class ClientNotFoundException extends NotFoundException {

    public ClientNotFoundException(UUID id) {
        super("Client", id);
    }
}