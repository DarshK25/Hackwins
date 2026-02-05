package com.moneyops.gateway.filter;

import com.moneyops.gateway.security.JwtTokenProvider;
import io.jsonwebtoken.Claims;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.WebFilter;
import org.springframework.web.server.WebFilterChain;
import reactor.core.publisher.Mono;

import java.util.List;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class AuthenticationFilter implements WebFilter {
    
    private final JwtTokenProvider jwtTokenProvider;
    
    @Value("#{'${gateway.public-endpoints}'.split(',')}")
    private List<String> publicEndpoints;
    
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, WebFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getPath().value();
        
        // Allow public endpoints
        if (isPublicEndpoint(path)) {
            return chain.filter(exchange);
        }
        
        // Extract token
        String token = extractToken(request);
        if (token == null) {
            log.warn("No authorization token found for path: {}", path);
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }
        
        try {
            // Validate token and extract claims FROM THE TOKEN
            UUID userId = jwtTokenProvider.getUserIdFromToken(token);
            UUID orgId = jwtTokenProvider.getOrgIdFromToken(token);
            
            // CRITICAL: Don't trust headers - extract from token
            // This prevents header spoofing attacks
            ServerHttpRequest mutatedRequest = request.mutate()
                .header("X-User-Id", userId.toString())
                .header("X-Org-Id", orgId.toString())
                .header("X-Auth-Token", token)
                .build();
            
            log.debug("Authenticated request for userId={}, orgId={}", userId, orgId);
            
            return chain.filter(exchange.mutate().request(mutatedRequest).build());
            
        } catch (SecurityException e) {
            log.error("Security validation failed: {}", e.getMessage());
            exchange.getResponse().setStatusCode(HttpStatus.FORBIDDEN);
            return exchange.getResponse().setComplete();
        } catch (Exception e) {
            log.error("Authentication error: {}", e.getMessage());
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }
    }
    
    private boolean isPublicEndpoint(String path) {
        return publicEndpoints.stream()
            .anyMatch(endpoint -> path.startsWith(endpoint.trim()));
    }
    
    private String extractToken(ServerHttpRequest request) {
        String bearerToken = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (bearerToken != null && bearerToken.startsWith("Bearer ")) {
            return bearerToken.substring(7);
        }
        return null;
    }
}