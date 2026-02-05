package com.ledgertalk.gateway.filter;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.time.Instant;

/**
 * RateLimitFilter - Redis-based Rate Limiting
 * 
 * PURPOSE:
 * - Prevent API abuse and brute force attacks
 * - Protect downstream services from overload
 * - Fair resource allocation per user/org/IP
 * 
 * BUSINESS LOGIC:
 * - Uses Redis for distributed rate limiting
 * - Token bucket algorithm with sliding window
 * - Configurable limits per endpoint type
 * 
 * RATE LIMITS:
 * - Login/Register: 10 requests/minute per IP
 * - Authenticated APIs: 50 requests/minute per user
 * - AI endpoints: 10 requests/minute per org
 * - Default: 100 requests/minute
 * 
 * REDIS KEYS:
 * - Format: rate_limit:{type}:{key}:{window}
 * - Example: rate_limit:ip:192.168.1.1:1643723400
 * - TTL: 60 seconds (sliding window)
 * 
 * HEADERS:
 * - X-RateLimit-Limit: Maximum requests allowed
 * - X-RateLimit-Remaining: Requests remaining in window
 * - X-RateLimit-Reset: Unix timestamp when limit resets
 * - Retry-After: Seconds to wait (on 429 response)
 */
@Slf4j
@Component
public class RateLimitFilter extends AbstractGatewayFilterFactory<RateLimitFilter.Config> {
    
    private final ReactiveStringRedisTemplate redisTemplate;
    
    @Value("${gateway.rate-limit.enabled:true}")
    private boolean rateLimitEnabled;
    
    public RateLimitFilter(ReactiveStringRedisTemplate redisTemplate) {
        super(Config.class);
        this.redisTemplate = redisTemplate;
    }
    
    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            // Skip if rate limiting is disabled
            if (!rateLimitEnabled) {
                log.debug("Rate limiting disabled - allowing request");
                return chain.filter(exchange);
            }
            
            String key = config.getKey();
            int limit = config.getLimit();
            int windowSeconds = config.getWindowSeconds();
            
            if (key == null || key.isBlank()) {
                log.warn("Rate limit key is null - skipping rate limit check");
                return chain.filter(exchange);
            }
            
            // Get current window (sliding window based on seconds)
            long currentWindow = Instant.now().getEpochSecond() / windowSeconds;
            String redisKey = String.format("rate_limit:%s:%d", key, currentWindow);
            
            return redisTemplate.opsForValue()
                .increment(redisKey)
                .flatMap(count -> {
                    // Set TTL on first request in window
                    if (count == 1) {
                        redisTemplate.expire(redisKey, Duration.ofSeconds(windowSeconds))
                            .subscribe();
                    }
                    
                    // Calculate remaining requests
                    long remaining = Math.max(0, limit - count);
                    long resetTime = (currentWindow + 1) * windowSeconds;
                    
                    // Add rate limit headers
                    exchange.getResponse().getHeaders().add("X-RateLimit-Limit", String.valueOf(limit));
                    exchange.getResponse().getHeaders().add("X-RateLimit-Remaining", String.valueOf(remaining));
                    exchange.getResponse().getHeaders().add("X-RateLimit-Reset", String.valueOf(resetTime));
                    
                    // Check if limit exceeded
                    if (count > limit) {
                        log.warn("Rate limit exceeded: key={}, limit={}, count={}", key, limit, count);
                        
                        exchange.getResponse().setStatusCode(HttpStatus.TOO_MANY_REQUESTS);
                        exchange.getResponse().getHeaders().add("Retry-After", String.valueOf(windowSeconds));
                        
                        return exchange.getResponse().setComplete();
                    }
                    
                    log.debug("Rate limit check passed: key={}, count={}/{}", key, count, limit);
                    return chain.filter(exchange);
                })
                .onErrorResume(e -> {
                    // On Redis error, allow request (fail-open)
                    log.error("Rate limit check failed - allowing request: {}", e.getMessage());
                    return chain.filter(exchange);
                });
        };
    }
    
    /**
     * Configuration for rate limiting
     */
    public static class Config {
        private String key;           // Redis key (e.g., IP, userId, orgId)
        private int limit = 100;      // Max requests per window
        private int windowSeconds = 60; // Time window in seconds
        
        public String getKey() {
            return key;
        }
        
        public void setKey(String key) {
            this.key = key;
        }
        
        public int getLimit() {
            return limit;
        }
        
        public void setLimit(int limit) {
            this.limit = limit;
        }
        
        public int getWindowSeconds() {
            return windowSeconds;
        }
        
        public void setWindowSeconds(int windowSeconds) {
            this.windowSeconds = windowSeconds;
        }
    }
}