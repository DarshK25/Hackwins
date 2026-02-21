package com.moneyops.events.producer;

import com.moneyops.events.dto.DomainEvent;

/**
 * Abstraction for publishing domain events. Implementations may use Kafka or no-op when Kafka is disabled.
 */
public interface IEventPublisher {

    void publish(DomainEvent event);
}
