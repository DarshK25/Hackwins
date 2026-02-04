package com.ledgertalk.gateway.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import reactor.core.publisher.Mono;

/**
 * RateLimitKeyResolverConfig - Key Resolvers for Rate Limiting
 * 
 * PURPOSE:
 * - Define how to extract rate limit keys from requests
 * - Support multiple rate limiting strategies
 * 
 * KEY RESOLVERS:
 * 1. IP-based: For public endpoints (login, register)
 * 2. User-based: For authenticated endpoints
 * 3. Org-based: For tenant-scoped endpoints
 * 4. Path-based: For specific endpoint limits
 * 
 * BUSINESS LOGIC:
 * - IP rate limit: Prevent brute force attacks
 * - User rate limit: Prevent individual user abuse
 * - Org rate limit: Fair resource allocation per tenant
 */
@Slf4j
@Configuration
public class RateLimitKeyResolverConfig {
    
    /**
     * IP-based KeyResolver
     * 
     * USE CASE: Public endpoints (login, register)
     * - Extracts client IP from request
     * - Supports X-Forwarded-For for proxied requests
     * - Prevents brute force attacks
     */
    @Bean
    @Primary
    public KeyResolver ipKeyResolver() {
        return exchange -> {
            // Check X-Forwarded-For header first (for load balancers/proxies)
            String xForwardedFor = exchange.getRequest().getHeaders().getFirst("X-Forwarded-For");
            if (xForwardedFor != null && !xForwardedFor.isBlank()) {
                // Take first IP (original client)
                String clientIp = xForwardedFor.split(",")[0].trim();
                log.debug("IP rate limit key from X-Forwarded-For: {}", clientIp);
                return Mono.just("ip:" + clientIp);
            }
            
            // Fallback to remote address
            String remoteAddr = exchange.getRequest().getRemoteAddress() != null
                ? exchange.getRequest().getRemoteAddress().getAddress().getHostAddress()
                : "unknown";
            
            log.debug("IP rate limit key from remote address: {}", remoteAddr);
            return Mono.just("ip:" + remoteAddr);
        };
    }
    
    /**
     * User-based KeyResolver
     * 
     * USE CASE: Authenticated endpoints
     * - Extracts userId from X-User-Id header (set by AuthenticationFilter)
     * - Prevents single user from abusing API
     * - Falls back to IP if user not authenticated
     */
    @Bean
    public KeyResolver userKeyResolver() {
        return exchange -> {
            String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
            
            if (userId != null && !userId.isBlank()) {
                log.debug("User rate limit key: {}", userId);
                return Mono.just("user:" + userId);
            }
            
            // Fallback to IP-based for unauthenticated requests
            log.debug("No userId found - falling back to IP-based rate limit");
            return ipKeyResolver().resolve(exchange);
        };
    }
    
    /**
     * Organization-based KeyResolver
     * 
     * USE CASE: Tenant-scoped endpoints
     * - Extracts orgId from X-Org-Id header (set by AuthenticationFilter)
     * - Prevents single tenant from consuming all resources
     * - Fair resource allocation across organizations
     */
    @Bean
    public KeyResolver orgKeyResolver() {
        return exchange -> {
            String orgId = exchange.getRequest().getHeaders().getFirst("X-Org-Id");
            
            if (orgId != null && !orgId.isBlank()) {
                log.debug("Org rate limit key: {}", orgId);
                return Mono.just("org:" + orgId);
            }
            
            // Fallback to user-based if no org context
            log.debug("No orgId found - falling back to user-based rate limit");
            return userKeyResolver().resolve(exchange);
        };
    }
    
    /**
     * Path-based KeyResolver
     * 
     * USE CASE: Specific endpoint limits
     * - Rate limit by specific path (e.g., /api/ai/chat)
     * - Global limit across all users
     * - Useful for expensive operations
     */
    @Bean
    public KeyResolver pathKeyResolver() {
        return exchange -> {
            String path = exchange.getRequest().getPath().value();
            
            // Normalize path (remove IDs for consistent keys)
            String normalizedPath = path.replaceAll("/\\d+", "/{id}")
                .replaceAll("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "{uuid}");
            
            log.debug("Path rate limit key: {}", normalizedPath);
            return Mono.just("path:" + normalizedPath);
        };
    }
    
    /**
     * Composite KeyResolver
     * 
     * USE CASE: Multiple rate limit dimensions
     * - Combines user + path for more granular control
     * - Example: Limit user to 10 AI requests/min + global 1000 AI requests/min
     */
    @Bean
    public KeyResolver compositeKeyResolver() {
        return exchange -> {
            String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
            String path = exchange.getRequest().getPath().value();
            
            String key = (userId != null ? "user:" + userId : "ip:unknown") + ":path:" + path;
            log.debug("Composite rate limit key: {}", key);
            return Mono.just(key);
        };
    }
}