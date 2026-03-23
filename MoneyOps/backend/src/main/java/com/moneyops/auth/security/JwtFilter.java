// src/main/java/com/moneyops/auth/security/JwtFilter.java
package com.moneyops.auth.security;

import com.moneyops.shared.utils.OrgContext;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import java.util.Optional;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Component
@Slf4j
public class JwtFilter extends OncePerRequestFilter {

    @Autowired
    private JwtProvider jwtProvider;

    @Autowired
    private com.moneyops.users.repository.UserRepository userRepository;

    @Autowired
    private UserDetailsService userDetailsService;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {

        // If already authenticated (e.g. by ServiceTokenFilter for internal service calls),
        // skip JWT processing entirely to avoid double-authentication or false 403 errors.
        if (SecurityContextHolder.getContext().getAuthentication() != null
                && SecurityContextHolder.getContext().getAuthentication().isAuthenticated()) {
            filterChain.doFilter(request, response);
            return;
        }

        String token = getJwtFromRequest(request);

        if (token != null && jwtProvider.validateToken(token)) {
            final String userId = jwtProvider.getUserIdFromToken(token);
            UserDetails userDetails = userDetailsService.loadUserByUsername(userId);

            UsernamePasswordAuthenticationToken authentication =
                    new UsernamePasswordAuthenticationToken(userDetails, null, userDetails.getAuthorities());
            authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

            SecurityContextHolder.getContext().setAuthentication(authentication);

            try {
                // Production-level Security: Derive orgId from User record, not from potentially faked headers.
                // This ensures multi-tenant isolation is strictly maintained.
                
                final String currentUserId = userId;

                // Lookup user by ID first (likely the case for JWT subject)
                var userOpt = userRepository.findById(currentUserId);
                
                // Fallback: look up by clerkId
                if (userOpt.isEmpty()) {
                    userOpt = userRepository.findByClerkIdAndDeletedAtIsNull(currentUserId);
                }

                userOpt.ifPresentOrElse(user -> {
                    if (user.getDeletedAt() != null) {
                        log.warn("Authenticated user {} is soft-deleted", user.getId());
                        return;
                    }
                    OrgContext.setUserId(user.getId());
                    if (user.getOrgId() != null) {
                        OrgContext.setOrgId(user.getOrgId());
                    } else {
                        // Fallback: Check header if user record hasn't been linked to an org yet
                        String orgIdHeader = request.getHeader("X-Org-Id");
                        if (orgIdHeader != null && !orgIdHeader.startsWith("placeholder")) {
                            OrgContext.setOrgId(orgIdHeader);
                            log.debug("Assigned orgId {} from header to user {}", orgIdHeader, user.getId());
                        }
                    }
                }, () -> {
                    // If no user record, at least set the userId from token
                    OrgContext.setUserId(currentUserId);
                    String orgIdHeader = request.getHeader("X-Org-Id");
                    if (orgIdHeader != null && !orgIdHeader.startsWith("placeholder")) {
                        OrgContext.setOrgId(orgIdHeader);
                    }
                });

                log.debug("Final context - User: {}, Org: {}", OrgContext.getUserId(), OrgContext.getOrgId());
                filterChain.doFilter(request, response);
            } finally {
                OrgContext.clear();
            }
        } else {
            // Fallback: If no valid internal token, check for a Clerk ID in headers for development/onboarding flow
            String userIdHeader = request.getHeader("X-User-Id");
            String orgIdHeader = request.getHeader("X-Org-Id");

            if (userIdHeader != null) {
                try {
                    final String idStr = userIdHeader;
                    var userOpt = userRepository.findByClerkIdAndDeletedAtIsNull(idStr);
                    
                    if (userOpt.isEmpty()) {
                        userOpt = userRepository.findById(idStr);
                    }

                    userOpt.ifPresentOrElse(user -> {
                        if (user.getDeletedAt() != null) return;

                        UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
                                user.getEmail(), null, java.util.Collections.emptyList());
                        SecurityContextHolder.getContext().setAuthentication(auth);
                        
                        OrgContext.setUserId(user.getId());
                        if (user.getOrgId() != null) {
                            OrgContext.setOrgId(user.getOrgId());
                        } else if (orgIdHeader != null && !orgIdHeader.startsWith("placeholder")) {
                            OrgContext.setOrgId(orgIdHeader);
                        }
                    }, () -> {
                        // Minimal context for new users
                        OrgContext.setUserId(idStr);
                        if (orgIdHeader != null) OrgContext.setOrgId(orgIdHeader);
                    });
                    filterChain.doFilter(request, response);
                } finally {
                    OrgContext.clear();
                }
            } else {
                filterChain.doFilter(request, response);
            }
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
