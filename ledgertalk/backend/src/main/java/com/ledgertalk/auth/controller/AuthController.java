// src/main/java/com/ledgertalk/auth/controller/AuthController.java
package com.ledgertalk.auth.controller;

import com.ledgertalk.auth.dto.LoginRequest;
import com.ledgertalk.auth.dto.RegisterRequest;
import com.ledgertalk.auth.dto.TokenResponse;
import com.ledgertalk.auth.service.AuthService;
import com.ledgertalk.shared.dto.ApiResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

    @PostMapping("/login")
    public ResponseEntity<ApiResponse<TokenResponse>> login(@RequestBody LoginRequest request) {
        TokenResponse token = authService.login(request);
        return ResponseEntity.ok(ApiResponse.success(token));
    }

    @PostMapping("/register")
    public ResponseEntity<ApiResponse<TokenResponse>> register(@RequestBody RegisterRequest request) {
        TokenResponse token = authService.register(request);
        return ResponseEntity.ok(ApiResponse.success(token));
    }
}