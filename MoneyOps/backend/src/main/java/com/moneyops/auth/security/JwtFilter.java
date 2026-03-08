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
import java.util.UUID;

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
                
                // Final variables for lambda capture
                final String finalUserId = userId;
                UUID tempId = null;
                try {
                    tempId = UUID.fromString(userId);
                } catch (IllegalArgumentException e) {
                    // Not a UUID
                }
                final UUID internalId = tempId;

                if (internalId != null) {
                    userRepository.findById(internalId).ifPresentOrElse(user -> {
                        OrgContext.setUserId(user.getId());
                        if (user.getOrgId() != null) {
                            OrgContext.setOrgId(user.getOrgId());
                        }
                    }, () -> {
                        OrgContext.setUserId(internalId);
                    });
                } else {
                    // Fallback: look up by clerkId since it wasn't a UUID
                    userRepository.findByClerkId(finalUserId).ifPresentOrElse(user -> {
                        OrgContext.setUserId(user.getId());
                        if (user.getOrgId() != null) {
                            OrgContext.setOrgId(user.getOrgId());
                        }
                    }, () -> {
                        log.warn("Authenticated token sub '{}' is not a UUID and no matching user record found", finalUserId);
                    });
                }

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
                    Optional<com.moneyops.users.entity.User> userOpt;
                    
                    if (idStr.startsWith("user_")) {
                        userOpt = userRepository.findByClerkId(idStr);
                    } else {
                        try {
                            userOpt = userRepository.findById(UUID.fromString(idStr));
                        } catch (Exception e) {
                            userOpt = Optional.empty();
                        }
                    }

                    userOpt.ifPresentOrElse(user -> {
                        UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
                                user.getEmail(), null, java.util.Collections.emptyList());
                        SecurityContextHolder.getContext().setAuthentication(auth);
                        
                        OrgContext.setUserId(user.getId());
                        if (user.getOrgId() != null) {
                            OrgContext.setOrgId(user.getOrgId());
                        } else if (orgIdHeader != null && !orgIdHeader.startsWith("placeholder")) {
                            try {
                                OrgContext.setOrgId(UUID.fromString(orgIdHeader));
                            } catch (Exception e) {}
                        }
                    }, () -> {
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
