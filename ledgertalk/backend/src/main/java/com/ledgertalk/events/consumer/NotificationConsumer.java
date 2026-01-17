// src/main/java/com/ledgertalk/events/consumer/NotificationConsumer.java
package com.ledgertalk.events.consumer;

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

@Service
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