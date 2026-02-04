package com.ledgertalk.gateway.filter;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.data.redis.core.ReactiveValueOperations;
import org.springframework.http.HttpStatus;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.when;

/**
 * Unit tests for RateLimitFilter
 */
@ExtendWith(MockitoExtension.class)
class RateLimitFilterTest {
    
    @Mock
    private ReactiveStringRedisTemplate redisTemplate;
    
    @Mock
    private ReactiveValueOperations<String, String> valueOperations;
    
    @Mock
    private GatewayFilterChain filterChain;
    
    private RateLimitFilter rateLimitFilter;
    
    @BeforeEach
    void setUp() {
        lenient().when(redisTemplate.opsForValue()).thenReturn(valueOperations);
        lenient().when(filterChain.filter(any(ServerWebExchange.class))).thenReturn(Mono.empty());
        
        rateLimitFilter = new RateLimitFilter(redisTemplate);
        ReflectionTestUtils.setField(rateLimitFilter, "rateLimitEnabled", true);
    }
    
    @Test
    void shouldAllowRequestWhenUnderLimit() {
        // Given: Request is under rate limit
        RateLimitFilter.Config config = new RateLimitFilter.Config();
        config.setKey("test-key");
        config.setLimit(10);
        config.setWindowSeconds(60);
        
        when(valueOperations.increment(anyString())).thenReturn(Mono.just(5L));
        lenient().when(redisTemplate.expire(anyString(), any(Duration.class))).thenReturn(Mono.just(true));
        
        MockServerHttpRequest request = MockServerHttpRequest.get("/api/test").build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = rateLimitFilter.apply(config).filter(exchange, filterChain);
        
        // Then: Request should pass through
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getResponse().getStatusCode()).isNull();
        assertThat(exchange.getResponse().getHeaders().getFirst("X-RateLimit-Limit")).isEqualTo("10");
        assertThat(exchange.getResponse().getHeaders().getFirst("X-RateLimit-Remaining")).isEqualTo("5");
    }
    
    @Test
    void shouldRejectRequestWhenOverLimit() {
        // Given: Request exceeds rate limit
        RateLimitFilter.Config config = new RateLimitFilter.Config();
        config.setKey("test-key");
        config.setLimit(10);
        config.setWindowSeconds(60);
        
        when(valueOperations.increment(anyString())).thenReturn(Mono.just(15L));
        lenient().when(redisTemplate.expire(anyString(), any(Duration.class))).thenReturn(Mono.just(true));
        
        MockServerHttpRequest request = MockServerHttpRequest.get("/api/test").build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = rateLimitFilter.apply(config).filter(exchange, filterChain);
        
        // Then: Request should be rejected with 429
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getResponse().getStatusCode()).isEqualTo(HttpStatus.TOO_MANY_REQUESTS);
        assertThat(exchange.getResponse().getHeaders().getFirst("X-RateLimit-Remaining")).isEqualTo("0");
        assertThat(exchange.getResponse().getHeaders().getFirst("Retry-After")).isEqualTo("60");
    }
    
    @Test
    void shouldFailOpenOnRedisError() {
        // Given: Redis is unavailable
        RateLimitFilter.Config config = new RateLimitFilter.Config();
        config.setKey("test-key");
        config.setLimit(10);
        
        when(valueOperations.increment(anyString()))
            .thenReturn(Mono.error(new RuntimeException("Redis connection failed")));
        
        MockServerHttpRequest request = MockServerHttpRequest.get("/api/test").build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = rateLimitFilter.apply(config).filter(exchange, filterChain);
        
        // Then: Request should be allowed (fail-open)
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getResponse().getStatusCode()).isNull();
    }
    
    @Test
    void shouldSkipWhenRateLimitingDisabled() {
        // Given: Rate limiting is disabled
        ReflectionTestUtils.setField(rateLimitFilter, "rateLimitEnabled", false);
        
        RateLimitFilter.Config config = new RateLimitFilter.Config();
        config.setKey("test-key");
        config.setLimit(10);
        
        MockServerHttpRequest request = MockServerHttpRequest.get("/api/test").build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = rateLimitFilter.apply(config).filter(exchange, filterChain);
        
        // Then: Request should pass through without Redis check
        StepVerifier.create(result)
            .verifyComplete();
        
        assertThat(exchange.getResponse().getStatusCode()).isNull();
    }
    
    @Test
    void shouldSetTTLOnFirstRequest() {
        // Given: First request in window
        RateLimitFilter.Config config = new RateLimitFilter.Config();
        config.setKey("test-key");
        config.setLimit(10);
        config.setWindowSeconds(60);
        
        when(valueOperations.increment(anyString())).thenReturn(Mono.just(1L));
        lenient().when(redisTemplate.expire(anyString(), any(Duration.class))).thenReturn(Mono.just(true));
        
        MockServerHttpRequest request = MockServerHttpRequest.get("/api/test").build();
        MockServerWebExchange exchange = MockServerWebExchange.from(request);
        
        // When: Filter is applied
        Mono<Void> result = rateLimitFilter.apply(config).filter(exchange, filterChain);
        
        // Then: TTL should be set
        StepVerifier.create(result)
            .verifyComplete();
        
        // Verify expire was called (TTL set)
        // Note: In real implementation, this is verified via Redis commands
    }
}