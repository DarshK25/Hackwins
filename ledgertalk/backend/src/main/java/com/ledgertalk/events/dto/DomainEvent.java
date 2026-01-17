// src/main/java/com/ledgertalk/events/dto/DomainEvent.java
package com.ledgertalk.events.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class DomainEvent {
    private String topic;
    private String key;
    private String payload;
    private long timestamp = System.currentTimeMillis();
}