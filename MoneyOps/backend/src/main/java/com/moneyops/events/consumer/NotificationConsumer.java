// src/main/java/com/moneyops/events/consumer/NotificationConsumer.java
package com.moneyops.events.consumer;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

@Service
@ConditionalOnProperty(name = "spring.kafka.enabled", havingValue = "true", matchIfMissing = false)
public class NotificationConsumer {

    @KafkaListener(topics = "invoice-events", groupId = "notification-group")
    public void handleInvoiceEvent(String message) {
        // Send notifications based on event
        System.out.println("Notification: " + message);
    }

    @KafkaListener(topics = "client-events", groupId = "notification-group")
    public void handleClientEvent(String message) {
        // Send notifications
        System.out.println("Notification: " + message);
    }
}