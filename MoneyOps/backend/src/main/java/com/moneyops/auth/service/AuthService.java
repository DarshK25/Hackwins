// src/main/java/com/moneyops/auth/service/AuthService.java
package com.moneyops.auth.service;

import com.moneyops.auth.dto.LoginRequest;
import com.moneyops.auth.dto.OAuthUserInfo;
import com.moneyops.auth.dto.RegisterRequest;
import com.moneyops.auth.dto.TokenResponse;
import com.moneyops.auth.security.JwtProvider;
import com.moneyops.organizations.entity.BusinessOrganization;
import com.moneyops.organizations.repository.BusinessOrganizationRepository;
import com.moneyops.shared.exceptions.ConflictException;
import com.moneyops.shared.exceptions.UnauthorizedException;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
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
        User user = userRepository.findByEmailAndDeletedAtIsNull(request.getEmail())
                .orElseThrow(() -> new UnauthorizedException("Invalid credentials"));

        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            throw new UnauthorizedException("Invalid credentials");
        }

        if (user.getStatus() != User.Status.ACTIVE) {
            throw new UnauthorizedException("User account is not active");
        }

        String token = jwtProvider.generateToken(user.getId());
        return new TokenResponse(token, null, "Bearer", 86400);
    }

    public TokenResponse register(RegisterRequest request) {
        if (userRepository.existsByEmailAndDeletedAtIsNull(request.getEmail())) {
            throw new ConflictException("User already exists");
        }

        // Create organization
        BusinessOrganization org = new BusinessOrganization();
        org.setLegalName(request.getOrgName());
        
        // ✨ Bootstrap ID until user is created
        org.setCreatedBy("BOOTSTRAP");
        BusinessOrganization savedOrg = orgRepository.save(org);

        // Create user
        User user = new User();
        user.setName(request.getName());
        user.setEmail(request.getEmail());
        user.setPasswordHash(passwordEncoder.encode(request.getPassword()));
        user.setRole(User.Role.OWNER);
        user.setStatus(User.Status.ACTIVE);
        user.setOrgId(savedOrg.getId());
        
        // Temporarily set createdBy/updatedBy for non-null constraints if enforced
        user.setCreatedBy("SELF");
        User savedUser = userRepository.save(user);

        // Now correct the parent references
        savedOrg.setCreatedBy(savedUser.getId());
        orgRepository.save(savedOrg);

        savedUser.setCreatedBy(savedUser.getId());
        savedUser.setUpdatedBy(savedUser.getId());
        userRepository.save(savedUser);

        String token = jwtProvider.generateToken(savedUser.getId());
        return new TokenResponse(token, null, "Bearer", 86400);
    }

    public String handleOAuth2Login(OAuthUserInfo userInfo) {
        // Find or create user
        User user = userRepository.findByEmailAndDeletedAtIsNull(userInfo.getEmail())
                .orElseGet(() -> {
                    User newUser = new User();
                    newUser.setName(userInfo.getName());
                    newUser.setEmail(userInfo.getEmail());
                    newUser.setRole(User.Role.STAFF);
                    newUser.setStatus(User.Status.ACTIVE);
                    
                    // OAuth bootstrap user
                    String bootstrapId = "OAUTH_BOOTSTRAP";
                    newUser.setOrgId(bootstrapId);
                    newUser.setCreatedBy(bootstrapId);
                    newUser.setUpdatedBy(bootstrapId);
                    newUser.setPasswordHash(passwordEncoder.encode(java.util.UUID.randomUUID().toString()));
                    return userRepository.save(newUser);
                });

        return jwtProvider.generateToken(user.getId());
    }
}
