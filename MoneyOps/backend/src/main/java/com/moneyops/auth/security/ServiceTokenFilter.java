// src/main/java/com/moneyops/auth/security/ServiceTokenFilter.java
package com.moneyops.auth.security;

import com.moneyops.shared.utils.OrgContext;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Collections;

/**
 * ServiceTokenFilter — authenticates internal service-to-service calls.
 *
 * The AI-Gateway (and any other internal service) sends a shared secret in the
 * {@code X-Service-Token} header together with {@code X-Org-Id} and
 * {@code X-User-Id} headers that identify which organisation / user triggered
 * the action.
 *
 * When the token matches, the request is granted {@code ROLE_SERVICE} authority
 * and Spring Security considers it authenticated — no user JWT is needed.
 *
 * Configure the shared secret in application.properties / .env:
 *   INTERNAL_SERVICE_TOKEN=<your-secret>
 *
 * The AI-Gateway must send the same value as {@code X-Service-Token}.
 */
@Component
public class ServiceTokenFilter extends OncePerRequestFilter {

    /** Injected from INTERNAL_SERVICE_TOKEN env var / property. */
    @Value("${INTERNAL_SERVICE_TOKEN:moneyops-internal-service-secret}")
    private String expectedToken;

    @org.springframework.beans.factory.annotation.Autowired
    private com.moneyops.users.repository.UserRepository userRepository;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain)
            throws ServletException, IOException {

        String serviceToken = request.getHeader("X-Service-Token");

        if (StringUtils.hasText(serviceToken) && serviceToken.equals(expectedToken)) {
            // Already authenticated? Don't double-authenticate.
            if (SecurityContextHolder.getContext().getAuthentication() == null) {

                // Build a minimal "service" authentication principal
                UsernamePasswordAuthenticationToken auth =
                        new UsernamePasswordAuthenticationToken(
                                "ai-gateway-service",
                                null,
                                Collections.singletonList(new SimpleGrantedAuthority("ROLE_SERVICE"))
                        );
                SecurityContextHolder.getContext().setAuthentication(auth);

                // Populate OrgContext so downstream services can resolve org/user
                try {
                    String orgIdHeader = request.getHeader("X-Org-Id");
                    String userIdHeader = request.getHeader("X-User-Id");

                    if (StringUtils.hasText(userIdHeader)) {
                        userRepository.findByClerkIdAndDeletedAtIsNull(userIdHeader).ifPresentOrElse(user -> {
                            OrgContext.setUserId(user.getId());
                            if (user.getOrgId() != null) {
                                OrgContext.setOrgId(user.getOrgId());
                            } else if (StringUtils.hasText(orgIdHeader)) {
                                OrgContext.setOrgId(orgIdHeader);
                            }
                        }, () -> {
                            // Fallback: If no user record found, treat as new/unregistered user but set IDs
                            OrgContext.setUserId(userIdHeader);
                            if (StringUtils.hasText(orgIdHeader)) {
                                OrgContext.setOrgId(orgIdHeader);
                            }
                        });
                    } else if (StringUtils.hasText(orgIdHeader)) {
                        OrgContext.setOrgId(orgIdHeader);
                    }

                    filterChain.doFilter(request, response);
                } finally {
                    OrgContext.clear();
                }
                return;
            }
        }

        // Not a service request — continue to the next filter (JWT or unauthenticated)
        filterChain.doFilter(request, response);
    }
}
