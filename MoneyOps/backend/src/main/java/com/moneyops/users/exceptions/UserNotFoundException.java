// src/main/java/com/moneyops/users/exceptions/UserNotFoundException.java
package com.moneyops.users.exceptions;

import com.moneyops.shared.exceptions.NotFoundException;

import java.util.UUID;

public class UserNotFoundException extends NotFoundException {

    public UserNotFoundException(UUID id) {
        super("User", id);
    }
}