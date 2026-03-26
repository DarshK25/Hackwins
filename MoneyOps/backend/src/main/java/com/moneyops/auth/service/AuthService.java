// src/main/java/com/moneyops/auth/service/AuthService.java
package com.moneyops.auth.service;

import com.moneyops.auth.dto.LoginRequest;
import com.moneyops.auth.dto.OAuthUserInfo;
import com.moneyops.auth.dto.RegisterRequest;
import com.moneyops.auth.dto.TokenResponse;
import com.moneyops.auth.security.JwtProvider;
import com.moneyops.shared.exceptions.UnauthorizedException;
import com.moneyops.shared.exceptions.ValidationException;
import com.moneyops.users.entity.User;
import com.moneyops.users.repository.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional
public class AuthService {

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private JwtProvider jwtProvider;

    public TokenResponse login(LoginRequest request) {
        throw new UnauthorizedException("Password-based authentication is disabled. Use Clerk.");
    }

    public TokenResponse register(RegisterRequest request) {
        throw new ValidationException("Password-based authentication is disabled. Use Clerk.");
    }

    public String handleOAuth2Login(OAuthUserInfo userInfo) {
        User user = userRepository.findByEmailAndDeletedAtIsNull(userInfo.getEmail())
                .orElseGet(() -> {
                    User newUser = new User();
                    newUser.setName(userInfo.getName());
                    newUser.setEmail(userInfo.getEmail());
                    newUser.setRole(User.Role.STAFF);
                    newUser.setStatus(User.Status.ACTIVE);

                    String bootstrapId = "OAUTH_BOOTSTRAP";
                    newUser.setOrgId(bootstrapId);
                    newUser.setCreatedBy(bootstrapId);
                    newUser.setUpdatedBy(bootstrapId);
                    return userRepository.save(newUser);
                });

        return jwtProvider.generateToken(user.getId());
    }
}
