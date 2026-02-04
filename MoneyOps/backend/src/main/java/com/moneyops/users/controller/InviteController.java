// src/main/java/com/moneyops/users/controller/InviteController.java
package com.moneyops.users.controller;

import com.moneyops.users.entity.Invite;
import com.moneyops.users.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/invites")
public class InviteController {

    @Autowired
    private UserService userService;

    @GetMapping("/pending")
    public ResponseEntity<List<Invite>> getPendingInvites(@RequestHeader("X-Org-Id") UUID orgId) {
        List<Invite> invites = userService.getPendingInvites(orgId);
        return ResponseEntity.ok(invites);
    }
}