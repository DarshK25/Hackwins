// src/main/java/com/moneyops/users/controller/UserController.java
package com.moneyops.users.controller;

import com.moneyops.users.dto.UserDto;
import com.moneyops.users.dto.CreateInviteRequest;
import com.moneyops.users.dto.AcceptInviteRequest;
import com.moneyops.users.service.UserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @Autowired
    private UserService userService;

    @GetMapping
    public ResponseEntity<List<UserDto>> getAllUsers(@RequestHeader("X-Org-Id") UUID orgId) {
        List<UserDto> users = userService.getAllUsers(orgId);
        return ResponseEntity.ok(users);
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserDto> getUserById(@PathVariable UUID id, @RequestHeader("X-Org-Id") UUID orgId) {
        UserDto user = userService.getUserById(id, orgId);
        return ResponseEntity.ok(user);
    }

    @PostMapping
    public ResponseEntity<UserDto> createUser(@RequestBody UserDto dto, @RequestHeader("X-Org-Id") UUID orgId, @RequestHeader("X-User-Id") UUID createdBy) {
        UserDto created = userService.createUser(dto, orgId, createdBy);
        return ResponseEntity.ok(created);
    }

    @PutMapping("/{id}")
    public ResponseEntity<UserDto> updateUser(@PathVariable UUID id, @RequestBody UserDto dto, @RequestHeader("X-Org-Id") UUID orgId, @RequestHeader("X-User-Id") UUID updatedBy) {
        UserDto updated = userService.updateUser(id, dto, orgId, updatedBy);
        return ResponseEntity.ok(updated);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteUser(@PathVariable UUID id, @RequestHeader("X-Org-Id") UUID orgId) {
        userService.deleteUser(id, orgId);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/search")
    public ResponseEntity<List<UserDto>> searchUsers(@RequestParam String q, @RequestHeader("X-Org-Id") UUID orgId) {
        List<UserDto> users = userService.searchUsers(orgId, q);
        return ResponseEntity.ok(users);
    }

    @PostMapping("/invite")
    public ResponseEntity<Void> createInvite(@RequestBody CreateInviteRequest request, @RequestHeader("X-Org-Id") UUID orgId, @RequestHeader("X-User-Id") UUID createdBy) {
        userService.createInvite(request, orgId, createdBy);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/accept-invite")
    public ResponseEntity<UserDto> acceptInvite(@RequestBody AcceptInviteRequest request) {
        UserDto user = userService.acceptInvite(request);
        return ResponseEntity.ok(user);
    }
}