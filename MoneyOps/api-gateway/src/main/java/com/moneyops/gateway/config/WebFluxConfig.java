package com.moneyops.gateway.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;
/**
 * WebFluxConfig - Additional WebFlux Configuration
 * 
 * PURPOSE:
 * - Configure ObjectMapper for JSON processing
 * - Define KeyResolvers for rate limiting (Phase 3)
 * - Register additional beans for gateway filters
 */
@Configuration
public class WebFluxConfig {
    /**
     * ObjectMapper for JSON processing in filters
     * Configured with Java 8 time support
     */
    @Bean
    public ObjectMapper objectMapper(){
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerModule(new JavaTimeModule());
        return mapper;
    }
    /**
     * IP-based KeyResolver for rate limiting
     * 
     * USE CASE: Public endpoints (login, register)
     * - Rate limit by client IP address
     * - Prevents brute force attacks
     * - Protects against DDoS
     */
    @Bean
    @org.springframework.context.annotation.Primary
    public KeyResolver ipKeyResolver(){
        return exchange -> {
            String clientIp = exchange.getRequest().getRemoteAddress() != null
            ? exchange.getRequest().getRemoteAddress().getAddress().getHostAddress()
            :"unknown";
            return Mono.just(clientIp);
        };

    }
    
    /**
     * User-based KeyResolver for rate limiting
     * 
     * USE CASE: Authenticated endpoints
     * - Rate limit by userId
     * - Prevents single user from abusing API
     * - Extracted from X-User-Id header (set by AuthenticationFilter)
     */
    @Bean
    public KeyResolver userKeyResolver() {
        return exchange -> {
            String userId = exchange.getRequest().getHeaders().getFirst("X-User-Id");
            return Mono.just(userId != null ? userId : "anonymous");
        };
    }
    
    /**
     * Organization-based KeyResolver for rate limiting
     * 
     * USE CASE: Tenant-scoped endpoints
     * - Rate limit by organization ID
     * - Prevents single tenant from consuming all resources
     * - Extracted from X-Org-Id header (set by AuthenticationFilter)
     */
    @Bean
    public KeyResolver orgKeyResolver() {
        return exchange -> {
            String orgId = exchange.getRequest().getHeaders().getFirst("X-Org-Id");
            return Mono.just(orgId != null ? orgId : "no-org");
        };
    }

}