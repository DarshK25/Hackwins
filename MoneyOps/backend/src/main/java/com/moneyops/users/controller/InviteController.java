// src/main/java/com/moneyops/users/controller/InviteController.java
package com.moneyops.users.controller;

import com.moneyops.users.dto.CreateInviteRequest;
import com.moneyops.users.dto.AcceptInviteRequest;
import com.moneyops.users.entity.Invite;
import com.moneyops.users.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
@RestController
@RequestMapping("/api/invites")
public class InviteController {

    @Autowired
    private UserService userService;

    @PostMapping
    public ResponseEntity<Invite> createInvite(
            @RequestBody CreateInviteRequest request,
            @RequestHeader("X-Org-Id") String orgId,
            @RequestHeader("X-User-Id") String userId) {
        return ResponseEntity.ok(userService.createInvite(request, orgId, userId));
    }

    @PostMapping("/accept")
    public ResponseEntity<?> acceptInvite(@RequestBody AcceptInviteRequest request) {
        return ResponseEntity.ok(userService.acceptInvite(request));
    }

    @GetMapping("/pending")
    public ResponseEntity<List<Invite>> getPendingInvites(@RequestHeader("X-Org-Id") String orgId) {
        List<Invite> invites = userService.getPendingInvites(orgId);
        return ResponseEntity.ok(invites);
    }
}