// src/main/java/com/moneyops/auth/security/JwtFilter.java
package com.moneyops.auth.security;

import com.moneyops.shared.utils.OrgContext;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

@Component
public class JwtFilter extends OncePerRequestFilter {

    @Autowired
    private JwtProvider jwtProvider;

    @Autowired
    private UserDetailsService userDetailsService;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        String token = getJwtFromRequest(request);

        if (token != null && jwtProvider.validateToken(token)) {
            String userId = jwtProvider.getUserIdFromToken(token);
            UserDetails userDetails = userDetailsService.loadUserByUsername(userId);

            UsernamePasswordAuthenticationToken authentication =
                    new UsernamePasswordAuthenticationToken(userDetails, null, userDetails.getAuthorities());
            authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

            SecurityContextHolder.getContext().setAuthentication(authentication);

            try {
                // Set org context from headers
                String orgIdHeader = request.getHeader("X-Org-Id");
                String userIdHeader = request.getHeader("X-User-Id");

                if (userIdHeader != null) {
                    // Validate that the header matches the authenticated user
                    if (!userIdHeader.equals(userId)) {
                        response.sendError(HttpServletResponse.SC_FORBIDDEN, "User ID header does not match authenticated user");
                        return;
                    }
                    OrgContext.setUserId(UUID.fromString(userId)); // Use trusted userId from token
                } else {
                    // Always set userId from token if not in header (or purely rely on token)
                    OrgContext.setUserId(UUID.fromString(userId));
                }

                if (orgIdHeader != null) {
                    OrgContext.setOrgId(UUID.fromString(orgIdHeader));
                }

                filterChain.doFilter(request, response);
            } finally {
                OrgContext.clear();
            }
        } else {
            filterChain.doFilter(request, response);
        }
    }

    private String getJwtFromRequest(HttpServletRequest request) {
        String bearerToken = request.getHeader("Authorization");
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }
}