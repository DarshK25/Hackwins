package com.moneyops.events.producer;

import com.moneyops.events.dto.DomainEvent;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * No-op implementation when Kafka is disabled. Events are discarded (e.g. local dev without broker).
 */
@Component
@ConditionalOnProperty(name = "spring.kafka.enabled", havingValue = "false", matchIfMissing = true)
public class NoOpEventPublisher implements IEventPublisher {

    @Override
    public void publish(DomainEvent event) {
        // no-op when Kafka is not enabled
    }
}