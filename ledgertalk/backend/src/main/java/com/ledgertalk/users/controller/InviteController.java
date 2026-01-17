// src/main/java/com/ledgertalk/users/controller/InviteController.java
package com.ledgertalk.users.controller;

import com.ledgertalk.users.entity.Invite;
import com.ledgertalk.users.service.UserService;
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