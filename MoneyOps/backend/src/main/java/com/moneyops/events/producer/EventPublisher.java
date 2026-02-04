// src/main/java/com/moneyops/events/producer/EventPublisher.java
package com.moneyops.events.producer;

import com.moneyops.events.dto.DomainEvent;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

@Component
public class EventPublisher {

    @Autowired(required = false)
    private KafkaTemplate<String, String> kafkaTemplate;

    public void publish(DomainEvent event) {
        if (kafkaTemplate != null) {
            kafkaTemplate.send(event.getTopic(), event.getKey(), event.getPayload());
        } else {
            System.out.println("Kafka not available. Skipping event: " + event.getTopic());
        }
    }
}