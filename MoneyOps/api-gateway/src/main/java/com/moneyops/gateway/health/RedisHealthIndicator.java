package com.ledgertalk.gateway.health;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.ReactiveHealthIndicator;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

import java.time.Duration;

/**
 * RedisHealthIndicator - Monitor Redis Connection Health
 * 
 * PURPOSE:
 * - Check Redis connectivity for rate limiting
 * - Provide health status for readiness probes
 * - Alert on Redis failures
 * 
 * BUSINESS LOGIC:
 * - Ping Redis server
 * - Report response time
 * - Mark as DOWN if Redis unavailable
 * 
 * HEALTH ENDPOINT:
 * - /actuator/health/redis
 * - Status: UP/DOWN
 * - Details: response time, error message
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class RedisHealthIndicator implements ReactiveHealthIndicator {
    
    private final ReactiveStringRedisTemplate redisTemplate;
    
    private static final String PING_COMMAND = "PING";
    private static final Duration TIMEOUT = Duration.ofSeconds(2);
    
    @Override
    public Mono<Health> health() {
        long startTime = System.currentTimeMillis();
        
        return redisTemplate.execute(connection -> connection.ping())
            .next()
            .map(response -> {
                long responseTime = System.currentTimeMillis() - startTime;
                
                log.debug("Redis health check successful: {}ms", responseTime);
                
                return Health.up()
                    .withDetail("response", response)
                    .withDetail("responseTime", responseTime + "ms")
                    .build();
            })
            .timeout(TIMEOUT)
            .onErrorResume(e -> {
                log.error("Redis health check failed: {}", e.getMessage());
                
                return Mono.just(Health.down()
                    .withDetail("error", e.getMessage())
                    .withDetail("note", "Rate limiting may be degraded")
                    .build());
            });
    }
}