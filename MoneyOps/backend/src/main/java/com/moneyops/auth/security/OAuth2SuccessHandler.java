// src/main/java/com/moneyops/auth/security/OAuth2SuccessHandler.java
package com.moneyops.auth.security;

import com.moneyops.auth.dto.OAuthUserInfo;
import com.moneyops.auth.service.AuthService;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.security.web.authentication.SimpleUrlAuthenticationSuccessHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;

@Component
public class OAuth2SuccessHandler extends SimpleUrlAuthenticationSuccessHandler {

    @Autowired
    private AuthService authService;

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response,
                                      Authentication authentication) throws IOException, ServletException {

        OAuth2User oauth2User = (OAuth2User) authentication.getPrincipal();

        OAuthUserInfo userInfo = new OAuthUserInfo();
        userInfo.setId(oauth2User.getAttribute("sub"));
        userInfo.setEmail(oauth2User.getAttribute("email"));
        userInfo.setName(oauth2User.getAttribute("name"));
        userInfo.setPicture(oauth2User.getAttribute("picture"));

        String token = authService.handleOAuth2Login(userInfo);

        // Redirect to frontend with token
        getRedirectStrategy().sendRedirect(request, response, "http://localhost:3000/oauth2/redirect?token=" + token);
    }
}