package com.ledgertalk.gateway.health;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.Status;
import org.springframework.data.redis.connection.ReactiveRedisConnection;
import org.springframework.data.redis.connection.ReactiveRedisConnectionFactory;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

/**
 * Unit tests for RedisHealthIndicator
 */
@ExtendWith(MockitoExtension.class)
class RedisHealthIndicatorTest {
    
    @Mock
    private ReactiveStringRedisTemplate redisTemplate;
    
    @Mock
    private ReactiveRedisConnectionFactory connectionFactory;
    
    @Mock
    private ReactiveRedisConnection connection;
    
    private RedisHealthIndicator healthIndicator;
    
    @BeforeEach
    void setUp() {
        healthIndicator = new RedisHealthIndicator(redisTemplate);
    }
    
    @Test
    void shouldReportUpWhenRedisIsHealthy() {
        // Given: Redis ping succeeds
        when(redisTemplate.execute(any(org.springframework.data.redis.core.ReactiveRedisCallback.class)))
            .thenReturn(Flux.just("PONG"));
        
        // When: Health check is performed
        Mono<Health> health = healthIndicator.health();
        
        // Then: Status should be UP
        StepVerifier.create(health)
            .assertNext(h -> {
                assertThat(h.getStatus()).isEqualTo(Status.UP);
                assertThat(h.getDetails()).containsKey("response");
                assertThat(h.getDetails()).containsKey("responseTime");
            })
            .verifyComplete();
    }
    
    @Test
    void shouldReportDownWhenRedisIsUnhealthy() {
        // Given: Redis ping fails
        when(redisTemplate.execute(any(org.springframework.data.redis.core.ReactiveRedisCallback.class)))
            .thenReturn(Flux.error(new RuntimeException("Connection refused")));
        
        // When: Health check is performed
        Mono<Health> health = healthIndicator.health();
        
        // Then: Status should be DOWN
        StepVerifier.create(health)
            .assertNext(h -> {
                assertThat(h.getStatus()).isEqualTo(Status.DOWN);
                assertThat(h.getDetails()).containsKey("error");
                assertThat(h.getDetails().get("error")).isNotNull();
            })
            .verifyComplete();
    }
    
    @Test
    void shouldReportDownOnTimeout() {
        // Given: Redis ping times out
        when(redisTemplate.execute(any(org.springframework.data.redis.core.ReactiveRedisCallback.class)))
            .thenReturn(Flux.never()); // Never completes (simulates timeout)
        
        // When: Health check is performed
        Mono<Health> health = healthIndicator.health();
        
        // Then: Should timeout and report DOWN
        StepVerifier.create(health)
            .assertNext(h -> {
                assertThat(h.getStatus()).isEqualTo(Status.DOWN);
            })
            .verifyComplete();
    }
}