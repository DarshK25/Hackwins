// src/main/java/com/moneyops/auth/service/AuthService.java
package com.moneyops.auth.service;

import com.moneyops.auth.dto.LoginRequest;
import com.moneyops.auth.dto.OAuthUserInfo;
import com.moneyops.auth.dto.RegisterRequest;
import com.moneyops.auth.dto.TokenResponse;
import com.moneyops.auth.security.JwtProvider;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.UUID;

@Service
@Transactional
public class AuthService {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private BusinessOrganizationRepository orgRepository;

    @Autowired
    private JwtProvider jwtProvider;

    @Autowired
    private PasswordEncoder passwordEncoder;

    public TokenResponse login(LoginRequest request) {
        User user = userRepository.findByEmailAndOrgId(request.getEmail(), null) // Need to handle org
                .orElseThrow(() -> new RuntimeException("Invalid credentials"));

        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new RuntimeException("Invalid credentials");
        }

        String token = jwtProvider.generateToken(user.getId().toString());
        return new TokenResponse(token, null, "Bearer", 86400);
    }

    public TokenResponse register(RegisterRequest request) {
        if (userRepository.existsByEmailAndOrgId(request.getEmail(), null)) {
            throw new RuntimeException("User already exists");
        }

        // Create organization
        BusinessOrganization org = new BusinessOrganization();
        org.setLegalName(request.getOrgName());
        org.setCreatedAt(LocalDateTime.now());
        org.setUpdatedAt(LocalDateTime.now());
        // Use a temporary creator to satisfy non-null constraint, will be corrected after user creation
        org.setCreatedBy(UUID.randomUUID());
        BusinessOrganization savedOrg = orgRepository.save(org);

        // Create user
        User user = new User();
        user.setName(request.getName());
        user.setEmail(request.getEmail());
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        user.setRole(User.Role.OWNER);
        user.setStatus(User.Status.ACTIVE);
        user.setOrgId(savedOrg.getId());
        user.setCreatedAt(LocalDateTime.now());
        user.setUpdatedAt(LocalDateTime.now());
        // Temporarily set createdBy/updatedBy to org id to satisfy non-null constraints
        user.setCreatedBy(savedOrg.getId());
        user.setUpdatedBy(savedOrg.getId());
        User savedUser = userRepository.save(user);

        // Now correct the org.createdBy to point to the actual user who created it
        savedOrg.setCreatedBy(savedUser.getId());
        orgRepository.save(savedOrg);

        // Also ensure user's createdBy/updatedBy reference themselves
        savedUser.setCreatedBy(savedUser.getId());
        savedUser.setUpdatedBy(savedUser.getId());
        userRepository.save(savedUser);

        String token = jwtProvider.generateToken(savedUser.getId().toString());
        return new TokenResponse(token, null, "Bearer", 86400);
    }

    public String handleOAuth2Login(OAuthUserInfo userInfo) {
        // Find or create user
        User user = userRepository.findByEmailAndOrgId(userInfo.getEmail(), null)
                .orElseGet(() -> {
                    User newUser = new User();
                    newUser.setName(userInfo.getName());
                    newUser.setEmail(userInfo.getEmail());
                    newUser.setRole(User.Role.STAFF);
                    newUser.setStatus(User.Status.ACTIVE);
                    newUser.setCreatedAt(LocalDateTime.now());
                    newUser.setUpdatedAt(LocalDateTime.now());
                    return userRepository.save(newUser);
                });

        return jwtProvider.generateToken(user.getId().toString());
    }
}