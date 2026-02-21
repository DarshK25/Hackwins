// src/main/java/com/moneyops/events/producer/KafkaEventProducer.java
package com.moneyops.events.producer;

import com.moneyops.events.dto.DomainEvent;
import org.springframework.stereotype.Service;

@Service
public class KafkaEventProducer {

    private final IEventPublisher eventPublisher;

    public KafkaEventProducer(IEventPublisher eventPublisher) {
        this.eventPublisher = eventPublisher;
    }

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