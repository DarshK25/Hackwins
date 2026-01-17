// src/main/java/com/ledgertalk/events/producer/KafkaEventProducer.java
package com.ledgertalk.events.producer;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ledgertalk.events.dto.DomainEvent;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class KafkaEventProducer {

    @Autowired
    private EventPublisher eventPublisher;

    // @Autowired
    // private ObjectMapper objectMapper;

    public void publishInvoiceCreated(String invoiceId, String orgId) {
        DomainEvent event = new DomainEvent();
        event.setTopic("invoice-events");
        event.setKey(invoiceId);
        event.setPayload("{\"eventType\":\"INVOICE_CREATED\",\"invoiceId\":\"" + invoiceId + "\",\"orgId\":\"" + orgId + "\"}");
        eventPublisher.publish(event);
    }

    public void publishClientCreated(String clientId, String orgId) {
        DomainEvent event = new DomainEvent();
        event.setTopic("client-events");
        event.setKey(clientId);
        event.setPayload("{\"eventType\":\"CLIENT_CREATED\",\"clientId\":\"" + clientId + "\",\"orgId\":\"" + orgId + "\"}");
        eventPublisher.publish(event);
    }

    // Add more event publishers as needed
}