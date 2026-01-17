// src/main/java/com/ledgertalk/events/producer/EventPublisher.java
package com.ledgertalk.events.producer;

import com.ledgertalk.events.dto.DomainEvent;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class EventPublisher {

    @Autowired
    private KafkaTemplate<String, String> kafkaTemplate;

    public void publish(DomainEvent event) {
        kafkaTemplate.send(event.getTopic(), event.getKey(), event.getPayload());
    }
}