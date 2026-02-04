package com.ledgertalk.gateway.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.ReactiveRedisConnectionFactory;
import org.springframework.data.redis.connection.RedisStandaloneConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceClientConfiguration;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.data.redis.core.ReactiveStringRedisTemplate;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;

/**
 * RedisConfig - Redis Connection Configuration
 * 
 * PURPOSE:
 * - Configure Redis connection for rate limiting
 * - Set up reactive Redis templates
 * - Handle connection pooling and timeouts
 * 
 * BUSINESS LOGIC:
 * - Uses Lettuce (reactive Redis client)
 * - Connection pooling for performance
 * - Timeout configurations for resilience
 * 
 * PRODUCTION CONSIDERATIONS:
 * - Use Redis Sentinel/Cluster for HA
 * - Configure connection pool based on load
 * - Monitor Redis performance
 */
@Slf4j
@Configuration
public class RedisConfig {
    
    @Value("${spring.data.redis.host:localhost}")
    private String redisHost;
    
    @Value("${spring.data.redis.port:6379}")
    private int redisPort;
    
    @Value("${spring.data.redis.password:}")
    private String redisPassword;
    
    @Value("${spring.data.redis.timeout:2000}")
    private long redisTimeout;
    
    /**
     * Configure Redis connection factory
     */
    @Bean
    public ReactiveRedisConnectionFactory reactiveRedisConnectionFactory() {
        RedisStandaloneConfiguration redisConfig = new RedisStandaloneConfiguration();
        redisConfig.setHostName(redisHost);
        redisConfig.setPort(redisPort);
        
        if (redisPassword != null && !redisPassword.isBlank()) {
            redisConfig.setPassword(redisPassword);
        }
        
        // Configure Lettuce client
        LettuceClientConfiguration clientConfig = LettuceClientConfiguration.builder()
            .commandTimeout(Duration.ofMillis(redisTimeout))
            .shutdownTimeout(Duration.ofMillis(100))
            .build();
        
        LettuceConnectionFactory factory = new LettuceConnectionFactory(redisConfig, clientConfig);
        
        log.info("Redis connection configured: {}:{}", redisHost, redisPort);
        
        return factory;
    }
    
    /**
     * Reactive String Redis Template (for rate limiting)
     */
    @Bean
    public ReactiveStringRedisTemplate reactiveStringRedisTemplate(
            ReactiveRedisConnectionFactory connectionFactory) {
        return new ReactiveStringRedisTemplate(connectionFactory);
    }
    
    /**
     * Generic Reactive Redis Template
     */
    @Bean
    public ReactiveRedisTemplate<String, String> reactiveRedisTemplate(
            ReactiveRedisConnectionFactory connectionFactory) {
        
        StringRedisSerializer serializer = new StringRedisSerializer();
        
        RedisSerializationContext<String, String> context = RedisSerializationContext
            .<String, String>newSerializationContext(serializer)
            .key(serializer)
            .value(serializer)
            .hashKey(serializer)
            .hashValue(serializer)
            .build();
        
        return new ReactiveRedisTemplate<>(connectionFactory, context);
    }
}