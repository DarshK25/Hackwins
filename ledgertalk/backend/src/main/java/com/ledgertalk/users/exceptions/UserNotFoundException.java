// src/main/java/com/ledgertalk/users/exceptions/UserNotFoundException.java
package com.ledgertalk.users.exceptions;

import com.ledgertalk.shared.exceptions.NotFoundException;

import java.util.UUID;

public class UserNotFoundException extends NotFoundException {

    public UserNotFoundException(UUID id) {
        super("User", id);
    }
}